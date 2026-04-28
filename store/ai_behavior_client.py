"""AI Behavior Service client for monolith integration."""

import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AIBehaviorServiceUnavailable(Exception):
    """Raised when AI Behavior Service is unavailable."""


class AIBehaviorServiceError(Exception):
    """Raised when AI Behavior Service returns a business error."""


class AIBehaviorClient:
    def __init__(
        self,
        service_url: Optional[str] = None,
        service_token: Optional[str] = None,
        timeout: int = 12,
    ):
        self.service_url = service_url or getattr(settings, "AI_BEHAVIOR_SERVICE_URL", "http://localhost:5006")
        self.service_token = service_token or getattr(
            settings,
            "AI_BEHAVIOR_SERVICE_TOKEN",
            "ai-behavior-service-token-123",
        )
        self.timeout = timeout
        self.base_url = f"{self.service_url}/api/v1/ai"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.service_token}",
        }

    def _handle(self, response: requests.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise AIBehaviorServiceUnavailable("Invalid response from AI Behavior Service") from exc

        if response.status_code in (200, 201):
            return data
        if response.status_code == 401:
            raise AIBehaviorServiceUnavailable("AI Behavior Service authentication failed")
        if response.status_code >= 500:
            raise AIBehaviorServiceUnavailable("AI Behavior Service unavailable")
        raise AIBehaviorServiceError(data.get("detail", "AI Behavior request failed"))

    def ingest_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/events",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI Behavior ingest_event request failed: %s", exc)
            raise AIBehaviorServiceUnavailable("Could not ingest behavior event") from exc

    def ingest_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {"events": events}
        try:
            response = requests.post(
                f"{self.base_url}/events/batch",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI Behavior ingest_batch request failed: %s", exc)
            raise AIBehaviorServiceUnavailable("Could not ingest behavior events") from exc

    def train(self, min_events: int = 50) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/train",
                json={"min_events": int(min_events)},
                headers=self._headers(),
                timeout=max(self.timeout, 30),
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI Behavior train request failed: %s", exc)
            raise AIBehaviorServiceUnavailable("Could not train AI behavior model") from exc

    def recommend(self, user_id: int, top_k: int = 5, candidate_products: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        payload = {
            "user_id": int(user_id),
            "top_k": int(top_k),
            "candidate_products": candidate_products or [],
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
            logger.warning("AI Behavior recommend request failed: %s", exc)
            raise AIBehaviorServiceUnavailable("Could not fetch AI behavior recommendations") from exc

    def rag_query(self, user_id: int, query: str, top_k: int = 5) -> Dict[str, Any]:
        payload = {
            "user_id": int(user_id),
            "query": query,
            "top_k": int(top_k),
        }
        try:
            response = requests.post(
                f"{self.base_url}/rag/query",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI Behavior rag_query request failed: %s", exc)
            raise AIBehaviorServiceUnavailable("Could not query AI behavior RAG") from exc

    def trends(self, top_k: int = 5) -> Dict[str, Any]:
        try:
            response = requests.post(
                f"{self.base_url}/trends",
                json={"top_k": int(top_k)},
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI Behavior trends request failed: %s", exc)
            raise AIBehaviorServiceUnavailable("Could not fetch AI behavior trends") from exc

    def alerts(self) -> Dict[str, Any]:
        try:
            response = requests.get(
                f"{self.base_url}/alerts",
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI Behavior alerts request failed: %s", exc)
            raise AIBehaviorServiceUnavailable("Could not fetch AI behavior alerts") from exc

    def chat(self, user_id: int, question: str, session_id: str = "web-session", context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "user_id": int(user_id),
            "session_id": session_id,
            "question": question,
            "context": context or {},
        }
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("AI Behavior chat request failed: %s", exc)
            raise AIBehaviorServiceUnavailable("Could not query AI behavior chat") from exc

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
