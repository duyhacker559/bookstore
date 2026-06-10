from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from fastapi import FastAPI, Header, HTTPException

from config import get_settings
from embedding import ProductEmbedder
from faiss_service import FaissVectorStore
from lstm_model import pad_sequence, softmax_top_k
from neo4j_service import Neo4jService
from rag_pipeline import RAGPipeline, combine_hybrid_score
from schemas import ChatbotRequest, ChatbotResponse, RecommendRequest, RecommendationItem, RecommendationResponse
from train import LSTMArtifacts, group_events_by_user, load_trained_lstm, train_lstm_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


class ServiceState:
    def __init__(self) -> None:
        self.graph_service = Neo4jService(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )

    def close(self) -> None:
        self.graph_service.close()


state = ServiceState()


def _check_auth(auth_header: Optional[str]) -> None:
    expected = f"Bearer {settings.auth_token}"
    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _as_dict(item: Any) -> Dict[str, Any]:
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if isinstance(item, dict):
        return item
    return {}


def _normalize_products(payload: RecommendRequest | ChatbotRequest) -> List[Dict[str, object]]:
    candidates = list(payload.candidate_products or [])
    if not candidates:
        context_hints = payload.context.get("catalog_hints") if isinstance(payload.context, dict) else None
        if isinstance(context_hints, list):
            candidates = context_hints

    normalized: List[Dict[str, object]] = []
    for raw in candidates:
        item = _as_dict(raw)
        product_id = item.get("product_id")
        if product_id is None:
            product_id = item.get("id")
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            continue
        normalized.append(
            {
                "product_id": product_id,
                "title": str(item.get("title") or ""),
                "description": str(item.get("description") or ""),
                "category": str(item.get("category") or item.get("product_type") or ""),
                "price": item.get("price"),
                "stock": item.get("stock"),
            }
        )

    candidate_ids = []
    for value in getattr(payload, "candidate_product_ids", []) or []:
        try:
            candidate_ids.append(int(value))
        except (TypeError, ValueError):
            continue
    if candidate_ids:
        allowed = set(candidate_ids)
        normalized = [item for item in normalized if int(item["product_id"]) in allowed]

    return normalized


def _normalize_events(payload: RecommendRequest | ChatbotRequest, user_id: Optional[int]) -> List[Dict[str, object]]:
    raw_events: List[Any] = list(payload.events or [])
    if not raw_events and isinstance(payload.context, dict):
        context_events = payload.context.get("behavior_events")
        if isinstance(context_events, list):
            raw_events = context_events

    normalized: List[Dict[str, object]] = []
    for raw in raw_events:
        item = _as_dict(raw)
        product_id = item.get("product_id")
        if product_id is None:
            continue
        try:
            product_id = int(product_id)
        except (TypeError, ValueError):
            continue
        action = str(item.get("action") or item.get("event_type") or "view").lower()
        timestamp = item.get("timestamp")
        if not timestamp:
            timestamp = datetime.utcnow().isoformat()
        normalized.append(
            {
                "user_id": int(item.get("user_id") or user_id or 0),
                "product_id": product_id,
                "action": action,
                "timestamp": str(timestamp),
            }
        )

    return normalized


def _build_query_text(payload: RecommendRequest | ChatbotRequest, products: List[Dict[str, object]], events: List[Dict[str, object]]) -> str:
    query_text = str(getattr(payload, "query", "") or "").strip()
    if not query_text and isinstance(payload.context, dict):
        query_text = str(payload.context.get("query_text") or payload.context.get("preferred_category") or "").strip()
    if not query_text and payload.session_events:
        query_text = " ".join(str(item) for item in payload.session_events[-6:])
    if query_text:
        return query_text

    product_lookup = {int(item["product_id"]): item for item in products}
    snippets: List[str] = []
    for event in events:
        product_id = int(event.get("product_id") or 0)
        if product_id in product_lookup:
            product = product_lookup[product_id]
            snippets.append(f"{product.get('title', '')} {product.get('description', '')}")
    return " ".join(snippets).strip()


def _get_lstm_predictions(
    artifacts: Optional[LSTMArtifacts],
    events: List[Dict[str, object]],
    user_id: int,
    top_k: int,
) -> List[Dict[str, object]]:
    if artifacts is None:
        return []

    events_by_user = group_events_by_user(events)
    user_events = events_by_user.get(int(user_id), [])
    if not user_events:
        product_ids = list(artifacts.vocabulary.product_to_idx.keys())[:top_k]
        return [{"product_id": product_id, "score": 0.05} for product_id in product_ids]

    product_sequence = [artifacts.vocabulary.encode(int(event["product_id"])) for event in user_events if int(event.get("product_id") or 0) > 0]
    if not product_sequence:
        product_ids = list(artifacts.vocabulary.product_to_idx.keys())[:top_k]
        return [{"product_id": product_id, "score": 0.05} for product_id in product_ids]

    window = pad_sequence(product_sequence, settings.sequence_length)
    with torch.no_grad():
        logits = artifacts.model(torch.tensor([window], dtype=torch.long))[0]
    return softmax_top_k(logits, artifacts.vocabulary, top_k=top_k)


def _combine_scores(
    lstm_hits: List[Dict[str, object]],
    graph_hits: List[Dict[str, object]],
    rag_hits: List[Dict[str, object]],
    top_k: int,
) -> List[RecommendationItem]:
    lstm_map = {int(item["product_id"]): float(item["score"]) for item in lstm_hits}
    graph_map = {int(item["product_id"]): float(item["score"]) for item in graph_hits}
    rag_map = {int(item["product_id"]): float(item["score"]) for item in rag_hits}

    sources: Dict[int, List[str]] = {}
    for pid in lstm_map:
        sources.setdefault(pid, []).append("lstm")
    for pid in graph_map:
        sources.setdefault(pid, []).append("graph")
    for pid in rag_map:
        sources.setdefault(pid, []).append("rag")

    ranked: List[RecommendationItem] = []
    product_ids = set(lstm_map) | set(graph_map) | set(rag_map)
    for product_id in product_ids:
        final_score = combine_hybrid_score(
            lstm_map.get(product_id, 0.0),
            graph_map.get(product_id, 0.0),
            rag_map.get(product_id, 0.0),
        )
        ranked.append(
            RecommendationItem(
                product_id=product_id,
                score=float(final_score),
                sources=sources.get(product_id, []),
                reason="blend",
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[: max(1, top_k)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_path).mkdir(parents=True, exist_ok=True)
    yield
    state.close()


app = FastAPI(
    title="Bookstore AI Service",
    version=settings.api_version,
    description="Hybrid AI service with LSTM, Neo4j, FAISS, RAG and FastAPI",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> Dict[str, object]:
    return {"service": "bookstore-ai-service", "status": "running", "version": settings.api_version}


@app.get("/health")
async def health() -> Dict[str, object]:
    return {"status": "healthy", "service": settings.service_name}


@app.post("/api/v1/recommend", response_model=RecommendationResponse)
async def recommend(payload: RecommendRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, List[RecommendationItem]]:
    _check_auth(authorization)

    products = _normalize_products(payload)
    events = _normalize_events(payload, payload.user_id)
    if not products:
        return {"recommendations": []}
    if products:
        state.graph_service.build_graph(products, events)

    vector_store = FaissVectorStore(ProductEmbedder())
    vector_store.build(products)
    query_text = _build_query_text(payload, products, events)
    rag_hits = []
    if query_text:
        rag_hits = [{"product_id": item.product_id, "score": item.score} for item in vector_store.search(query_text, top_k=max(1, payload.top_k * 2))]

    graph_hits = [{"product_id": item.product_id, "score": item.score} for item in state.graph_service.query_recommendation(payload.user_id, top_k=max(1, payload.top_k * 2))]

    lstm_artifacts = load_trained_lstm(settings.checkpoint_path)
    if lstm_artifacts is None and events and products:
        lstm_artifacts = train_lstm_model(
            events=events,
            product_catalog=products,
            sequence_length=settings.sequence_length,
            embedding_dim=settings.embedding_dim,
            hidden_dim=settings.lstm_hidden_dim,
            lstm_layers=settings.lstm_layers,
            epochs=6,
            checkpoint_path=None,
        )

    lstm_hits = _get_lstm_predictions(lstm_artifacts, events, payload.user_id, top_k=max(1, payload.top_k * 2))
    recommendations = _combine_scores(lstm_hits, graph_hits, rag_hits, top_k=payload.top_k)

    return {"recommendations": recommendations}


@app.post("/api/v1/chatbot", response_model=ChatbotResponse)
async def chatbot(payload: ChatbotRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, object]:
    _check_auth(authorization)

    products = _normalize_products(payload)
    events = _normalize_events(payload, payload.user_id)
    if not products:
        return {
            "answer": "No product catalog was provided.",
            "citations": [],
            "recommended_products": [],
            "rag_chunks": [],
            "source": "hybrid",
        }
    if products:
        state.graph_service.build_graph(products, events)

    vector_store = FaissVectorStore(ProductEmbedder())
    vector_store.build(products)
    rag_pipeline = RAGPipeline(vector_store, state.graph_service)

    query_text = payload.question.strip()
    retrieval = rag_pipeline.retrieve(query_text, user_id=payload.user_id, top_k=payload.top_k)
    combined = retrieval.get("combined", [])

    recommended_products = [int(item.get("product_id")) for item in combined if item.get("product_id")]
    recommended_products = recommended_products[: max(1, payload.top_k)]

    answer = rag_pipeline.generate_response(query_text, user_id=payload.user_id, top_k=payload.top_k)
    citations = [item.get("title") for item in combined[:3] if item.get("title")]

    return {
        "answer": answer,
        "citations": citations,
        "recommended_products": recommended_products,
        "rag_chunks": retrieval.get("vector_hits", []),
        "source": "hybrid",
    }


@app.post("/api/v1/chat", response_model=ChatbotResponse)
async def chat_alias(payload: ChatbotRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, object]:
    return await chatbot(payload, authorization)
