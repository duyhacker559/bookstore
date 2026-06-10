"""AI behavior training client for staff actions."""

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class AIBehaviorUnavailable(Exception):
    """Raised when AI behavior service is unavailable."""


class AIBehaviorError(Exception):
    """Raised when AI behavior service returns a business error."""


class AIBehaviorClient:
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

    def train(self, min_events: int = 50) -> Dict[str, Any]:
        payload = {"min_events": int(min_events)}
        endpoint = f"{self.base_url}/train"
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            logger.warning("AI train request failed: %s", exc)
            raise AIBehaviorUnavailable("AI training service unavailable") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise AIBehaviorUnavailable("Invalid response from AI training service") from exc

        if response.status_code in (200, 201):
            return data
        if response.status_code == 404:
            return {
                "status": "skipped",
                "reason": "training_not_supported",
                "deep_learning": {"trained": False, "trained_samples": 0},
            }
        if response.status_code == 401:
            raise AIBehaviorUnavailable("AI training authentication failed")
        if response.status_code >= 500:
            raise AIBehaviorUnavailable("AI training service unavailable")
        raise AIBehaviorError(data.get("detail", "AI training failed"))
