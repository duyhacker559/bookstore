"""
Stripe Payment Service Integration
"""

import logging
import stripe
import time
from typing import Dict, Any, Optional
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Stripe payment processing service"""
    
    @staticmethod
    def create_charge(
        amount: float,
        currency: str,
        source: str,
        description: str,
        receipt_email: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a charge using Stripe.
        
        Args:
            amount: Amount in dollars (will be converted to cents)
            currency: Currency code (e.g., 'USD')
            source: Payment method ID or token
            description: Charge description
            receipt_email: Customer email for receipt
            idempotency_key: Idempotency key for retry safety
            
        Returns:
            Dictionary with charge details
            
        Raises:
            stripe.error.CardError: Card declined
            stripe.error.StripeError: Other Stripe errors
        """
        try:
            # Local/dev fallback: avoid real Stripe dependency when using demo key.
            if settings.STRIPE_SECRET_KEY == 'sk_test_demo':
                fake_id = f"ch_demo_{int(time.time())}"
                return {
                    'id': fake_id,
                    'status': 'succeeded',
                    'amount': amount,
                    'currency': currency.upper(),
                    'description': description,
                    'receipt_email': receipt_email,
                    'created': int(time.time()),
                }

            headers = {}
            if idempotency_key:
                headers['Idempotency-Key'] = idempotency_key
            
            charge = stripe.Charge.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                source=source,
                description=description,
                receipt_email=receipt_email,
                **({'headers': headers} if headers else {})
            )
            
            logger.info(f"Charge created: {charge.id} for amount {amount} {currency}")
            
            return {
                'id': charge.id,
                'status': 'succeeded' if charge.paid else 'pending',
                'amount': charge.amount / 100,  # Convert back to dollars
                'currency': charge.currency.upper(),
                'description': charge.description,
                'receipt_email': charge.receipt_email,
                'created': charge.created,
            }
            
        except stripe.error.CardError as e:
            logger.error(f"Card error: {e.user_message}")
            raise
        except stripe.error.RateLimitError as e:
            logger.error(f"Rate limit error: {e}")
            raise
        except stripe.error.AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            raise
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error: {e}")
            raise
    
    @staticmethod
    def create_refund(
        charge_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a refund for a charge.
        
        Args:
            charge_id: ID of the charge to refund
            amount: Optional amount to refund (in dollars)
            reason: Reason for refund
            
        Returns:
            Dictionary with refund details
        """
        try:
            refund_params = {
                'charge': charge_id,
                'reason': reason or 'requested_by_customer',
            }
            
            if amount:
                refund_params['amount'] = int(amount * 100)  # Convert to cents
            
            refund = stripe.Refund.create(**refund_params)
            
            logger.info(f"Refund created: {refund.id} for charge {charge_id}")
            
            return {
                'id': refund.id,
                'status': refund.status,
                'amount': refund.amount / 100,  # Convert back to dollars
                'charge_id': refund.charge,
                'reason': refund.reason,
                'created': refund.created,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Refund error: {e}")
            raise
    
    @staticmethod
    def retrieve_charge(charge_id: str) -> Dict[str, Any]:
        """
        Retrieve details of a charge.
        
        Args:
            charge_id: ID of the charge
            
        Returns:
            Dictionary with charge details
        """
        try:
            charge = stripe.Charge.retrieve(charge_id)
            
            return {
                'id': charge.id,
                'status': 'succeeded' if charge.paid else 'pending',
                'amount': charge.amount / 100,
                'currency': charge.currency.upper(),
                'description': charge.description,
                'receipt_email': charge.receipt_email,
                'created': charge.created,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving charge: {e}")
            raise
    
    @staticmethod
    def validate_webhook_signature(
        payload: bytes,
        signature: str,
        webhook_secret: str
    ) -> bool:
        """
        Validate Stripe webhook signature.
        
        Args:
            payload: Raw request body
            signature: Stripe signature header
            webhook_secret: Webhook signing secret
            
        Returns:
            True if signature is valid
        """
        try:
            stripe.Webhook.construct_event(payload, signature, webhook_secret)
            return True
        except ValueError:
            logger.error("Invalid webhook payload")
            return False
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            return False
