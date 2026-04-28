import logging
from typing import Optional

from fastapi import FastAPI, Header, HTTPException

from config import get_settings
from database import BehaviorStore
from schemas import (
    BatchEventsIn,
    BehaviorEventIn,
    ChatRequest,
    RagQueryRequest,
    RecommendRequest,
    TrainRequest,
    TrendRequest,
)
from services.chatbot import generate_with_gemini
from services.knowledge_graph import KnowledgeGraphEngine
from services.modeling import ModelState, predict_user_propensity, recommend_products, train_deep_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="AI microservice: behavior DB, deep learning, knowledge graph, RAG and chatbot",
)

store = BehaviorStore(settings.DB_PATH)
graph_engine = KnowledgeGraphEngine()
model_state = ModelState()


def _check_auth(auth_header: Optional[str]) -> None:
    expected = f"Bearer {settings.AUTH_TOKEN}"
    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _refresh_graph() -> dict:
    events = store.all_events()
    return graph_engine.rebuild(events)


@app.get("/")
async def root() -> dict:
    return {
        "service": "ai-behavior-service",
        "status": "running",
        "version": settings.API_VERSION,
    }


@app.get("/health")
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "ai-behavior-service",
        "version": settings.API_VERSION,
        "events": store.total_events(),
    }


@app.post("/api/v1/ai/events")
async def ingest_event(payload: BehaviorEventIn, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    inserted = store.insert_events([payload.model_dump()])
    return {"status": "ok", "inserted": inserted}


@app.post("/api/v1/ai/events/batch")
async def ingest_events_batch(payload: BatchEventsIn, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    inserted = store.insert_events([event.model_dump() for event in payload.events])
    return {"status": "ok", "inserted": inserted}


@app.post("/api/v1/ai/train")
async def train_models(payload: TrainRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    all_events = store.all_events()

    if len(all_events) < payload.min_events:
        return {
            "trained": False,
            "reason": "min_events_not_reached",
            "current_events": len(all_events),
            "required_events": payload.min_events,
        }

    deep_result = train_deep_model(model_state, all_events)
    graph_stats = graph_engine.rebuild(all_events)

    return {
        "status": "completed",
        "deep_learning": deep_result,
        "knowledge_graph": graph_stats,
    }


@app.post("/api/v1/ai/graph/rebuild")
async def rebuild_graph(authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    stats = _refresh_graph()
    return {"status": "rebuilt", "graph": stats}


@app.post("/api/v1/ai/rag/query")
async def rag_query(payload: RagQueryRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    if graph_engine.graph.number_of_nodes() == 0:
        _refresh_graph()

    chunks = graph_engine.rag_retrieve(user_id=payload.user_id, query=payload.query, top_k=payload.top_k)
    gnn_trends = graph_engine.gnn_predict_categories(user_id=payload.user_id, top_k=min(payload.top_k, 5))
    return {
        "user_id": payload.user_id,
        "query": payload.query,
        "chunks": chunks,
        "gnn_trends": gnn_trends,
    }


@app.post("/api/v1/ai/recommend")
async def recommend(payload: RecommendRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    user_events = store.events_for_user(payload.user_id, limit=400)

    propensity = predict_user_propensity(model_state, user_events)
    recs = recommend_products(user_events=user_events, candidates=payload.candidate_products, top_k=payload.top_k)

    if graph_engine.graph.number_of_nodes() == 0:
        _refresh_graph()
    category_trends = graph_engine.gnn_predict_categories(payload.user_id, top_k=5)

    return {
        "user_id": payload.user_id,
        "purchase_propensity": propensity,
        "recommendations": recs,
        "category_trends": category_trends,
        "model_version": "ai-behavior-v1",
    }


@app.post("/api/v1/ai/trends")
async def trends(payload: TrendRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    category_counts = store.category_counts()
    event_counts = store.event_type_counts()

    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[: payload.top_k]
    top_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[: payload.top_k]

    return {
        "top_categories": [{"category": c, "count": v} for c, v in top_categories],
        "top_events": [{"event_type": e, "count": v} for e, v in top_events],
        "total_events": store.total_events(),
    }


@app.get("/api/v1/ai/alerts")
async def alerts(authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    event_counts = store.event_type_counts()

    negative_events = event_counts.get("removeCart", 0) + event_counts.get("refund", 0)
    purchase_events = event_counts.get("purchase", 0) + event_counts.get("checkout", 0)
    total = max(store.total_events(), 1)

    negative_ratio = negative_events / total
    conversion_ratio = purchase_events / total

    alert_items = []
    if negative_ratio > 0.2:
        alert_items.append(
            {
                "level": "high",
                "type": "negative_trend",
                "message": "Ty le hanh vi tieu cuc dang tang cao, can danh gia lai UX/price.",
                "value": round(negative_ratio, 4),
            }
        )
    if conversion_ratio < 0.05 and total > 50:
        alert_items.append(
            {
                "level": "medium",
                "type": "low_conversion",
                "message": "Ty le chuyen doi thap, nen toi uu trang chi tiet va quy trinh thanh toan.",
                "value": round(conversion_ratio, 4),
            }
        )

    if not alert_items:
        alert_items.append(
            {
                "level": "info",
                "type": "stable",
                "message": "Chua ghi nhan xu huong bat thuong.",
                "value": round(conversion_ratio, 4),
            }
        )

    return {
        "alerts": alert_items,
        "negative_ratio": round(negative_ratio, 4),
        "conversion_ratio": round(conversion_ratio, 4),
    }


@app.post("/api/v1/ai/chat")
async def chat(payload: ChatRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)

    if graph_engine.graph.number_of_nodes() == 0:
        _refresh_graph()

    rag_chunks = graph_engine.rag_retrieve(user_id=payload.user_id, query=payload.question, top_k=5)
    gnn_trends = graph_engine.gnn_predict_categories(user_id=payload.user_id, top_k=5)

    fallback_answer = "Mình gợi ý bạn xem các sản phẩm thuộc nhóm bạn đã tương tác nhiều gần đây để tăng khả năng phù hợp."

    ai_answer = generate_with_gemini(
        api_key=settings.GOOGLE_API_KEY,
        model=settings.GEMINI_MODEL,
        api_version=settings.GEMINI_API_VERSION,
        question=payload.question,
        rag_chunks=rag_chunks,
        trend_categories=gnn_trends,
        fallback_answer=fallback_answer,
    )

    return {
        "session_id": payload.session_id,
        "user_id": payload.user_id,
        "answer": ai_answer or fallback_answer,
        "source": "gemini" if ai_answer else "rule-fallback",
        "rag_chunks": rag_chunks,
        "gnn_trends": gnn_trends,
    }
