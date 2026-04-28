"""Behavior Service client for monolith integration."""

import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BehaviorServiceUnavailable(Exception):
    """Raised when Behavior Service is unavailable."""


class BehaviorServiceError(Exception):
    """Raised when Behavior Service returns a business error."""


class BehaviorClient:
    def __init__(
        self,
        service_url: Optional[str] = None,
        service_token: Optional[str] = None,
        timeout: int = 8,
    ):
        self.service_url = service_url or getattr(settings, "BEHAVIOR_SERVICE_URL", "http://localhost:5004")
        self.service_token = service_token or getattr(
            settings,
            "BEHAVIOR_SERVICE_TOKEN",
            "behavior-service-token-123",
        )
        self.timeout = timeout
        self.base_url = f"{self.service_url}/api/v1/behavior"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.service_token}",
        }

    def _handle(self, response: requests.Response) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise BehaviorServiceUnavailable("Invalid response from Behavior Service") from exc

        if response.status_code == 200:
            return data
        if response.status_code == 401:
            raise BehaviorServiceUnavailable("Behavior Service authentication failed")
        if response.status_code >= 500:
            raise BehaviorServiceUnavailable("Behavior Service unavailable")
        raise BehaviorServiceError(data.get("detail", "Behavior request failed"))

    def recommend(
        self,
        user_id: int,
        candidate_product_ids: Optional[List[int]] = None,
        top_k: int = 5,
        candidate_products: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "user_id": user_id,
            "candidate_product_ids": candidate_product_ids or [],
            "candidate_products": candidate_products or [],
            "context": context or {},
            "top_k": top_k,
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
            logger.warning("Behavior recommend request failed: %s", exc)
            raise BehaviorServiceUnavailable("Could not fetch behavior recommendations") from exc

    def score(self, user_id: int, session_events: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "user_id": user_id,
            "session_events": session_events or [],
            "context": context or {},
        }
        try:
            response = requests.post(
                f"{self.base_url}/score",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            return self._handle(response)
        except requests.RequestException as exc:
            logger.warning("Behavior score request failed: %s", exc)
            raise BehaviorServiceUnavailable("Could not score user behavior") from exc

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
