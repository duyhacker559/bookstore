"""RAG Service client for monolith integration."""

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class RAGServiceUnavailable(Exception):
    """Raised when RAG Service is unavailable."""


class RAGServiceError(Exception):
    """Raised when RAG Service returns a business error."""


class RAGClient:
    def __init__(
        self,
        service_url: Optional[str] = None,
        service_token: Optional[str] = None,
        timeout: int = 12,
    ):
        self.service_url = service_url or getattr(settings, "RAG_SERVICE_URL", "http://localhost:5005")
        self.service_token = service_token or getattr(
            settings,
            "RAG_SERVICE_TOKEN",
            "rag-service-token-123",
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
            raise RAGServiceUnavailable("Invalid response from RAG Service") from exc

        if response.status_code == 200:
            return data
        if response.status_code == 401:
            raise RAGServiceUnavailable("RAG Service authentication failed")
        if response.status_code >= 500:
            raise RAGServiceUnavailable("RAG Service unavailable")
        raise RAGServiceError(data.get("detail", "RAG request failed"))

    def query_chat(self, session_id: str, user_id: int, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "question": question,
            "context": context or {},
        }
        try:
            response = requests.post(
                f"{self.base_url}/chat/query",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("RAG query request failed: %s", exc)
            raise RAGServiceUnavailable("Could not query RAG chat") from exc

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
