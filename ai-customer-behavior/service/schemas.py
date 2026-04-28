from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BehaviorEventIn(BaseModel):
    user_id: int
    product_id: int
    action: str
    timestamp: datetime
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProductIn(BaseModel):
    product_id: int
    title: str
    description: str = ""
    category: str = ""


class RecommendRequest(BaseModel):
    user_id: int


class ChatbotRequest(BaseModel):
    message: str
    user_id: Optional[int] = None


class RecommendationResponse(BaseModel):
    recommendations: List[int]


class ChatbotResponse(BaseModel):
    response: str
