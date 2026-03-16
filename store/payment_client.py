"""
Payment Service Client for Monolith

This module provides a client for the monolith to communicate with the
external Payment Service microservice.

Usage:
    from store.payment_client import PaymentClient
    
    client = PaymentClient()
    result = client.process_payment(
        order_id='order-123',
        amount=99.99,
        customer_email='customer@example.com',
        payment_method_id='tok_visa'
    )
"""

import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class PaymentServiceUnavailable(Exception):
    """Raised when Payment Service is unavailable"""
    pass


class PaymentProcessingError(Exception):
    """Raised when payment processing fails"""
    pass


class PaymentClient:
    """Client for Payment Service communication"""
    
    def __init__(
        self,
        service_url: Optional[str] = None,
        service_token: Optional[str] = None,
        timeout: int = 10
    ):
        """
        Initialize Payment Service client.
        
        Args:
            service_url: Payment Service URL (defaults to settings.PAYMENT_SERVICE_URL)
            service_token: API token (defaults to settings.PAYMENT_SERVICE_TOKEN)
            timeout: Request timeout in seconds
        """
        self.service_url = service_url or getattr(
            settings,
            'PAYMENT_SERVICE_URL',
            'http://localhost:5000'
        )
        self.service_token = service_token or getattr(
            settings,
            'PAYMENT_SERVICE_TOKEN',
            'development-token'
        )
        self.timeout = timeout
        self.base_url = f"{self.service_url}/api/v1"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.service_token}',
        }
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle Payment Service response"""
        try:
            data = response.json()
        except ValueError:
            logger.error(f"Invalid JSON response from Payment Service: {response.text}")
            raise PaymentServiceUnavailable("Payment Service returned invalid response")
        
        if response.status_code == 200:
            return data
        elif response.status_code == 402:
            raise PaymentProcessingError(data.get('detail', 'Payment declined'))
        elif response.status_code == 401:
            logger.error("Payment Service authentication failed")
            raise PaymentServiceUnavailable("Payment Service authentication failed")
        elif response.status_code == 404:
            raise PaymentProcessingError(data.get('detail', 'Payment not found'))
        elif response.status_code >= 500:
            logger.error(f"Payment Service error: {response.status_code} - {data}")
            raise PaymentServiceUnavailable("Payment Service error")
        else:
            logger.error(f"Payment Service error: {response.status_code} - {data}")
            raise PaymentProcessingError(
                data.get('error', f"Payment processing failed ({response.status_code})")
            )
    
    def process_payment(
        self,
        order_id: str,
        amount: float,
        customer_email: str,
        payment_method_id: str,
        currency: str = 'USD'
    ) -> Dict[str, Any]:
        """
        Process a payment via the Payment Service.
        
        Args:
            order_id: Unique order identifier
            amount: Payment amount in dollars
            customer_email: Customer email address
            payment_method_id: Stripe payment method ID or token
            currency: Currency code (default: USD)
            
        Returns:
            Dictionary with payment details
            
        Raises:
            PaymentServiceUnavailable: If Payment Service is down
            PaymentProcessingError: If payment processing fails
            
        Example:
            >>> result = client.process_payment(
            ...     order_id='order-123',
            ...     amount=99.99,
            ...     customer_email='customer@example.com',
            ...     payment_method_id='tok_visa'
            ... )
            >>> print(result['status'])
            'succeeded'
        """
        
        logger.info(f"Processing payment for order {order_id} via Payment Service")
        
        payload = {
            'order_id': order_id,
            'amount': amount,
            'currency': currency,
            'customer_email': customer_email,
            'payment_method_id': payment_method_id,
        }
        
        try:
            response = requests.post(
                f'{self.base_url}/payments/process',
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            return self._handle_response(response)
            
        except requests.ConnectionError:
            logger.error(f"Connection error connecting to Payment Service: {self.service_url}")
            raise PaymentServiceUnavailable(
                "Could not connect to Payment Service. Please try again later."
            )
        except requests.Timeout:
            logger.error("Payment Service request timed out")
            raise PaymentServiceUnavailable(
                "Payment Service request timed out. Please try again later."
            )
        except Exception as e:
            logger.error(f"Unexpected error calling Payment Service: {e}")
            raise PaymentServiceUnavailable("Payment Service error occurred")
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund a payment via the Payment Service.
        
        Args:
            payment_id: Stripe charge/payment ID
            amount: Optional amount to refund (full refund if omitted)
            reason: Reason for refund
            
        Returns:
            Dictionary with refund details
            
        Raises:
            PaymentServiceUnavailable: If Payment Service is down
            PaymentProcessingError: If refund processing fails
        """
        
        logger.info(f"Processing refund for payment {payment_id}")
        
        payload = {
            'payment_id': payment_id,
            'reason': reason,
        }
        
        if amount:
            payload['amount'] = amount
        
        try:
            response = requests.post(
                f'{self.base_url}/payments/refund',
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            return self._handle_response(response)
            
        except (PaymentServiceUnavailable, PaymentProcessingError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Payment Service: {e}")
            raise PaymentServiceUnavailable("Payment Service error occurred")
    
    def get_payment_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get payment status for an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            Dictionary with payment details
            
        Raises:
            PaymentServiceUnavailable: If Payment Service is down
            PaymentProcessingError: If order not found
        """
        
        try:
            response = requests.get(
                f'{self.base_url}/payments/{order_id}',
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            
            return self._handle_response(response)
            
        except (PaymentServiceUnavailable, PaymentProcessingError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Payment Service: {e}")
            raise PaymentServiceUnavailable("Payment Service error occurred")
    
    def health_check(self) -> bool:
        """
        Check if Payment Service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = requests.get(
                f'{self.service_url}/health',
                timeout=5,
            )
            return response.status_code == 200
        except Exception:
            return False
