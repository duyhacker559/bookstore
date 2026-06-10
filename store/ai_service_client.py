"""Unified AI Service client for monolith integration."""

import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AIServiceUnavailable(Exception):
    """Raised when AI Service is unavailable."""


class AIServiceError(Exception):
    """Raised when AI Service returns a business error."""


class AIServiceClient:
    def __init__(
        self,
        service_url: Optional[str] = None,
        service_token: Optional[str] = None,
        timeout: int = 12,
    ):
        self.service_url = service_url or getattr(settings, "AI_SERVICE_URL", "http://localhost:5006")
        self.service_token = service_token or getattr(
            settings,
            "AI_SERVICE_TOKEN",
            "ai-service-token-123",
        )
        self.timeout = timeout
        self.base_url = f"{self.service_url}/api/v1"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.service_token}",
        }

    def _handle(self, response: requests.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise AIServiceUnavailable("Invalid response from AI Service") from exc

        if response.status_code in (200, 201):
            return data
        if response.status_code == 401:
            raise AIServiceUnavailable("AI Service authentication failed")
        if response.status_code >= 500:
            raise AIServiceUnavailable("AI Service unavailable")
        raise AIServiceError(data.get("detail", "AI request failed"))

    def recommend(
        self,
        user_id: int,
        top_k: int = 5,
        candidate_product_ids: Optional[List[int]] = None,
        candidate_products: Optional[List[Dict[str, Any]]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        session_events: Optional[List[str]] = None,
        query: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "user_id": int(user_id),
            "top_k": int(top_k),
            "candidate_product_ids": candidate_product_ids or [],
            "candidate_products": candidate_products or [],
            "events": events or [],
            "session_events": session_events or [],
            "query": query or "",
            "context": context or {},
        }
        try:
            response = requests.post(
                f"{self.base_url}/recommend",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI recommend request failed: %s", exc)
            raise AIServiceUnavailable("Could not fetch AI recommendations") from exc

    def chat(
        self,
        user_id: Optional[int],
        session_id: str,
        question: str,
        candidate_products: Optional[List[Dict[str, Any]]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        session_events: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        payload = {
            "user_id": int(user_id) if user_id is not None else None,
            "session_id": session_id,
            "question": question,
            "candidate_products": candidate_products or [],
            "events": events or [],
            "session_events": session_events or [],
            "context": context or {},
            "top_k": int(top_k),
        }
        try:
            response = requests.post(
                f"{self.base_url}/chatbot",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI chat request failed: %s", exc)
            raise AIServiceUnavailable("Could not query AI chat") from exc

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
