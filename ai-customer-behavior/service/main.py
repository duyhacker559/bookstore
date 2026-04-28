from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional

import torch
from fastapi import FastAPI, Header, HTTPException

from config import get_settings
from embedding import ProductEmbedder
from lstm_model import pad_sequence, softmax_top_k
from neo4j_service import Neo4jService
from rag_pipeline import RAGPipeline, combine_hybrid_score
from schemas import ChatbotRequest, ChatbotResponse, RecommendRequest, RecommendationResponse
from train import LSTMArtifacts, group_events_by_user, load_demo_events, load_demo_products, load_trained_lstm, train_lstm_model
from faiss_service import FaissVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()


class ServiceState:
    def __init__(self) -> None:
        self.products = load_demo_products()
        self.events = load_demo_events()
        self.events_by_user = group_events_by_user(self.events)
        self.lstm_artifacts: Optional[LSTMArtifacts] = None
        self.vector_store = FaissVectorStore(ProductEmbedder())
        self.graph_service = Neo4jService(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
            database=settings.neo4j_database,
        )
        self.rag_pipeline: Optional[RAGPipeline] = None


state = ServiceState()


def _check_auth(auth_header: Optional[str]) -> None:
    expected = f"Bearer {settings.auth_token}"
    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _bootstrap_models() -> None:
    checkpoint = load_trained_lstm(settings.checkpoint_path)
    if checkpoint is None:
        checkpoint = train_lstm_model(
            events=state.events,
            product_catalog=state.products,
            sequence_length=settings.sequence_length,
            embedding_dim=settings.embedding_dim,
            hidden_dim=settings.lstm_hidden_dim,
            lstm_layers=settings.lstm_layers,
            epochs=20,
            checkpoint_path=settings.checkpoint_path,
        )
    state.lstm_artifacts = checkpoint
    state.vector_store.build(state.products)
    state.graph_service.build_graph(state.products, state.events)
    state.rag_pipeline = RAGPipeline(state.vector_store, state.graph_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.data_path).mkdir(parents=True, exist_ok=True)
    _bootstrap_models()
    yield
    state.graph_service.close()


app = FastAPI(
    title="Bookstore AI Service",
    version=settings.api_version,
    description="Hybrid AI service with LSTM, Neo4j, FAISS, RAG and FastAPI",
    lifespan=lifespan,
)


def _get_lstm_predictions(user_id: int, top_k: int) -> List[Dict[str, object]]:
    artifacts = state.lstm_artifacts
    if artifacts is None:
        return []

    user_events = state.events_by_user.get(int(user_id), [])
    if not user_events:
        product_ids = list(artifacts.vocabulary.product_to_idx.keys())[:top_k]
        return [{"product_id": product_id, "score": 0.1} for product_id in product_ids]

    product_sequence = [artifacts.vocabulary.encode(int(event["product_id"])) for event in user_events if int(event.get("product_id") or 0) > 0]
    if not product_sequence:
        product_ids = list(artifacts.vocabulary.product_to_idx.keys())[:top_k]
        return [{"product_id": product_id, "score": 0.1} for product_id in product_ids]

    window = pad_sequence(product_sequence, settings.sequence_length)
    with torch.no_grad():
        logits = artifacts.model(torch.tensor([window], dtype=torch.long))[0]
    return softmax_top_k(logits, artifacts.vocabulary, top_k=top_k)


def _get_graph_predictions(user_id: int, top_k: int) -> List[Dict[str, object]]:
    return [{"product_id": item.product_id, "score": item.score} for item in state.graph_service.query_recommendation(user_id, top_k=top_k)]


def _get_rag_predictions(user_id: int, top_k: int) -> List[Dict[str, object]]:
    user_events = state.events_by_user.get(int(user_id), [])
    if not user_events:
        return []

    product_lookup = {int(product["product_id"]): product for product in state.products}
    query_text = " ".join(
        f"{product_lookup.get(int(event['product_id']), {}).get('title', '')} {product_lookup.get(int(event['product_id']), {}).get('description', '')}"
        for event in user_events
        if int(event.get("product_id") or 0) > 0
    ).strip()
    if not query_text:
        return []

    vector_hits = state.vector_store.search(query_text, top_k=top_k)
    return [{"product_id": item.product_id, "score": item.score} for item in vector_hits]


def _score_recommendations(user_id: int, top_k: int) -> List[int]:
    lstm_hits = _get_lstm_predictions(user_id, top_k=max(top_k * 2, top_k))
    graph_hits = _get_graph_predictions(user_id, top_k=max(top_k * 2, top_k))
    rag_hits = _get_rag_predictions(user_id, top_k=max(top_k * 2, top_k))

    lstm_map = {int(item["product_id"]): float(item["score"]) for item in lstm_hits}
    graph_map = {int(item["product_id"]): float(item["score"]) for item in graph_hits}
    rag_map = {int(item["product_id"]): float(item["score"]) for item in rag_hits}

    product_ids = set(lstm_map) | set(graph_map) | set(rag_map)
    ranked: List[tuple[int, float]] = []
    for product_id in product_ids:
        final_score = combine_hybrid_score(
            lstm_map.get(product_id, 0.0),
            graph_map.get(product_id, 0.0),
            rag_map.get(product_id, 0.0),
        )
        ranked.append((product_id, final_score))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return [product_id for product_id, _ in ranked[: max(1, top_k)]]


@app.get("/")
async def root() -> Dict[str, object]:
    return {"service": "bookstore-ai-service", "status": "running", "version": settings.api_version}


@app.get("/health")
async def health() -> Dict[str, object]:
    return {
        "status": "healthy",
        "service": settings.service_name,
        "products": len(state.products),
        "users": len(state.events_by_user),
    }


@app.post("/api/v1/recommend", response_model=RecommendationResponse)
async def recommend(payload: RecommendRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, List[int]]:
    _check_auth(authorization)
    recommendations = _score_recommendations(payload.user_id, settings.recommendation_top_k)
    return {"recommendations": recommendations}


@app.post("/api/v1/chatbot", response_model=ChatbotResponse)
async def chatbot(payload: ChatbotRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, str]:
    _check_auth(authorization)
    if state.rag_pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

    response = state.rag_pipeline.generate_response(payload.message, user_id=payload.user_id, top_k=5)
    return {"response": response}