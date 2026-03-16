"""Shipping Service client for monolith integration."""

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ShippingServiceUnavailable(Exception):
    """Raised when Shipping Service is unavailable."""


class ShippingProcessingError(Exception):
    """Raised when shipping operation fails."""


class ShippingClient:
    def __init__(
        self,
        service_url: Optional[str] = None,
        service_token: Optional[str] = None,
        timeout: int = 10,
    ):
        self.service_url = service_url or getattr(settings, "SHIPPING_SERVICE_URL", "http://localhost:5001")
        self.service_token = service_token or getattr(
            settings,
            "SHIPPING_SERVICE_TOKEN",
            "shipping-service-token-123",
        )
        self.timeout = timeout
        self.base_url = f"{self.service_url}/api/v1/shipping"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.service_token}",
        }

    def _handle(self, response: requests.Response) -> Dict[str, Any] | list[Dict[str, Any]]:
        try:
            data = response.json()
        except ValueError as exc:
            raise ShippingServiceUnavailable("Invalid response from Shipping Service") from exc

        if response.status_code == 200:
            return data
        if response.status_code == 401:
            raise ShippingServiceUnavailable("Shipping Service authentication failed")
        if response.status_code == 404:
            raise ShippingProcessingError(data.get("detail", "Shipment not found"))
        if response.status_code >= 500:
            raise ShippingServiceUnavailable("Shipping Service unavailable")
        raise ShippingProcessingError(data.get("detail", "Shipping request failed"))

    def get_shipping_options(self, weight: float = 1.0) -> list[Dict[str, Any]]:
        try:
            response = requests.get(
                f"{self.base_url}/options",
                params={"weight": weight},
                headers=self._headers(),
                timeout=self.timeout,
            )
            data = self._handle(response)
            return data if isinstance(data, list) else []
        except requests.RequestException as exc:
            logger.warning("Shipping options request failed: %s", exc)
            raise ShippingServiceUnavailable("Could not fetch shipping options") from exc

    def create_shipment(
        self,
        order_id: str,
        address: str,
        method_code: str,
        fee: float,
    ) -> Dict[str, Any]:
        payload = {
            "order_id": order_id,
            "address": address,
            "method_code": method_code,
            "fee": fee,
        }
        try:
            response = requests.post(
                f"{self.base_url}/create",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            data = self._handle(response)
            return data if isinstance(data, dict) else {}
        except requests.RequestException as exc:
            logger.warning("Create shipment request failed: %s", exc)
            raise ShippingServiceUnavailable("Could not create shipment") from exc

    def get_shipment_status(self, order_id: str) -> Dict[str, Any]:
        try:
            response = requests.get(
                f"{self.base_url}/{order_id}",
                headers=self._headers(),
                timeout=self.timeout,
            )
            data = self._handle(response)
            return data if isinstance(data, dict) else {}
        except requests.RequestException as exc:
            logger.warning("Shipment status request failed: %s", exc)
            raise ShippingServiceUnavailable("Could not fetch shipment status") from exc

    def update_shipment_status(self, order_id: str, status: str) -> Dict[str, Any]:
        payload = {"status": status}
        try:
            response = requests.put(
                f"{self.base_url}/{order_id}",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            data = self._handle(response)
            return data if isinstance(data, dict) else {}
        except requests.RequestException as exc:
            logger.warning("Shipment status update request failed: %s", exc)
            raise ShippingServiceUnavailable("Could not update shipment status") from exc

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
