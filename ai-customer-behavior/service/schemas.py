from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BehaviorEventIn(BaseModel):
    user_id: int
    event_type: str
    session_id: Optional[str] = None
    product_id: Optional[int] = None
    category: Optional[str] = None
    query_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ts: Optional[datetime] = None


class BatchEventsIn(BaseModel):
    events: List[BehaviorEventIn] = Field(default_factory=list)


class TrainRequest(BaseModel):
    min_events: int = 50


class RecommendRequest(BaseModel):
    user_id: int
    top_k: int = 5
    candidate_products: List[Dict[str, Any]] = Field(default_factory=list)


class RagQueryRequest(BaseModel):
    user_id: int
    query: str
    top_k: int = 5


class TrendRequest(BaseModel):
    top_k: int = 5


class ChatRequest(BaseModel):
    user_id: int
    session_id: str = "default"
    question: str
    context: Dict[str, Any] = Field(default_factory=dict)
