from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BehaviorEventIn(BaseModel):
    user_id: int
    product_id: int
    action: str
    timestamp: Optional[datetime] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProductIn(BaseModel):
    product_id: int
    title: str = ""
    description: str = ""
    category: str = ""
    price: Optional[float] = None
    stock: Optional[int] = None


class RecommendRequest(BaseModel):
    user_id: int
    top_k: int = 5
    candidate_products: List[ProductIn] = Field(default_factory=list)
    candidate_product_ids: List[int] = Field(default_factory=list)
    events: List[BehaviorEventIn] = Field(default_factory=list)
    session_events: List[str] = Field(default_factory=list)
    query: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)


class ChatbotRequest(BaseModel):
    question: str
    user_id: Optional[int] = None
    session_id: str = "web-session"
    candidate_products: List[ProductIn] = Field(default_factory=list)
    events: List[BehaviorEventIn] = Field(default_factory=list)
    session_events: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    top_k: int = 5


class RecommendationItem(BaseModel):
    product_id: int
    score: float
    sources: List[str] = Field(default_factory=list)
    reason: str = ""


class RecommendationResponse(BaseModel):
    recommendations: List[RecommendationItem]


class ChatbotResponse(BaseModel):
    answer: str
    citations: List[str] = Field(default_factory=list)
    recommended_products: List[int] = Field(default_factory=list)
    rag_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "hybrid"
