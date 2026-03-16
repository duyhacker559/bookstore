"""
Payment Routes
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Header, status
from fastapi.responses import JSONResponse
from typing import Optional
from sqlalchemy.orm import Session

from config import get_settings
from schemas import (
    PaymentRequest,
    PaymentResponse,
    PaymentErrorResponse,
    RefundRequest,
    RefundResponse,
)
from services.stripe_service import StripeService
from services.event_publisher import EventPublisher
from database import get_db
from models import Payment, PaymentStatus
import stripe

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1", tags=["payments"])

# Initialize services
event_publisher = EventPublisher(
    host=settings.RABBITMQ_HOST,
    port=settings.RABBITMQ_PORT,
    username=settings.RABBITMQ_USER,
    password=settings.RABBITMQ_PASSWORD,
)


def verify_auth(authorization: Optional[str] = Header(None)) -> bool:
    """Verify API token authentication"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format"
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Validate token (can be from monolith or other service)
    if token not in [settings.AUTH_TOKEN, settings.MONOLITH_TOKEN]:
        logger.warning(f"Invalid token attempt: {token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return True


@router.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "payment-service",
        "version": "1.0.0"
    }


@router.post("/payments/process", response_model=PaymentResponse)
async def process_payment(
    request: PaymentRequest,
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_auth),
):
    """
    Process a payment using Stripe.
    
    - **order_id**: Unique order identifier from monolith
    - **amount**: Payment amount in dollars
    - **currency**: Currency code (USD, EUR, etc)
    - **customer_email**: Customer email for receipt
    - **payment_method_id**: Stripe token or payment method ID
    """
    
    logger.info(f"Processing payment for order {request.order_id}")
    
    try:
        # Check if payment already exists (idempotency)
        existing_payment = db.query(Payment).filter(
            Payment.order_id == request.order_id
        ).first()
        
        if existing_payment:
            if existing_payment.status == PaymentStatus.COMPLETED:
                logger.warning(f"Payment already processed for order {request.order_id}")
                return PaymentResponse(
                    status="already_processed",
                    payment_id=existing_payment.transaction_id,
                    order_id=request.order_id,
                    amount=existing_payment.amount,
                    currency=existing_payment.currency,
                    transaction_id=existing_payment.transaction_id,
                    message="Payment already processed for this order"
                )
            elif existing_payment.status == PaymentStatus.PROCESSING:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Payment already in progress for this order"
                )
        
        # Create payment record (pending)
        payment = Payment(
            order_id=request.order_id,
            customer_email=request.customer_email,
            amount=request.amount,
            currency=request.currency,
            payment_method_id=request.payment_method_id,
            status=PaymentStatus.PROCESSING,
        )
        db.add(payment)
        db.commit()
        
        # Process with Stripe
        stripe_response = StripeService.create_charge(
            amount=request.amount,
            currency=request.currency,
            source=request.payment_method_id,
            description=f"Order {request.order_id}",
            receipt_email=request.customer_email,
            idempotency_key=request.order_id,
        )
        
        # Update payment record
        payment.status = PaymentStatus.COMPLETED
        payment.transaction_id = stripe_response['id']
        db.commit()
        
        # Publish success event
        event_publisher.publish_payment_completed(
            order_id=request.order_id,
            transaction_id=stripe_response['id'],
            amount=request.amount,
            customer_email=request.customer_email,
            correlation_id=request.order_id,
        )
        
        logger.info(f"Payment processed successfully: {stripe_response['id']}")
        
        return PaymentResponse(
            status="succeeded",
            payment_id=stripe_response['id'],
            order_id=request.order_id,
            amount=request.amount,
            currency=request.currency,
            transaction_id=stripe_response['id'],
            message="Payment processed successfully"
        )
        
    except stripe.error.CardError as e:
        # Card declined or other card error
        payment.status = PaymentStatus.FAILED
        payment.error_message = str(e)
        db.commit()
        
        event_publisher.publish_payment_failed(
            order_id=request.order_id,
            error_message=str(e),
            correlation_id=request.order_id,
        )
        
        logger.error(f"Card error for order {request.order_id}: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e),
            headers={"X-Error-Code": "card_declined"}
        )
        
    except stripe.error.StripeError as e:
        # Other Stripe errors
        if payment:
            payment.status = PaymentStatus.FAILED
            payment.error_message = str(e)
            db.commit()
            
            event_publisher.publish_payment_failed(
                order_id=request.order_id,
                error_message=str(e),
                correlation_id=request.order_id,
            )
        
        logger.error(f"Stripe error for order {request.order_id}: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing failed"
        )
        
    except Exception as e:
        # Unexpected error
        if payment:
            payment.status = PaymentStatus.FAILED
            payment.error_message = str(e)
            db.commit()
        
        logger.error(f"Unexpected error processing payment: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing failed"
        )


@router.post("/payments/refund", response_model=RefundResponse)
async def refund_payment(
    request: RefundRequest,
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_auth),
):
    """
    Refund a payment.
    
    - **payment_id**: Stripe charge/payment ID to refund
    - **amount**: Optional amount to refund (full refund if omitted)
    - **reason**: Reason for refund
    """
    
    logger.info(f"Processing refund for payment {request.payment_id}")
    
    try:
        # Process refund with Stripe
        refund_response = StripeService.create_refund(
            charge_id=request.payment_id,
            amount=request.amount,
            reason=request.reason,
        )
        
        # Update payment record if we have it
        payment = db.query(Payment).filter(
            Payment.transaction_id == request.payment_id
        ).first()
        
        if payment:
            if request.amount and request.amount < payment.amount:
                payment.status = PaymentStatus.COMPLETED  # Partial refund
            else:
                payment.status = PaymentStatus.REFUNDED
            db.commit()
        
        logger.info(f"Refund processed successfully: {refund_response['id']}")
        
        return RefundResponse(
            status="succeeded",
            refund_id=refund_response['id'],
            payment_id=request.payment_id,
            amount=refund_response['amount'],
            message="Refund processed successfully"
        )
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe refund error: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund failed: {str(e)}"
        )
        
    except Exception as e:
        logger.error(f"Unexpected error processing refund: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Refund processing failed"
        )


@router.get("/payments/{order_id}")
async def get_payment_status(
    order_id: str,
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_auth),
):
    """Get payment status for an order"""
    
    payment = db.query(Payment).filter(
        Payment.order_id == order_id
    ).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment not found for order {order_id}"
        )
    
    return {
        "order_id": payment.order_id,
        "status": payment.status.value,
        "amount": payment.amount,
        "currency": payment.currency,
        "transaction_id": payment.transaction_id,
        "created_at": payment.created_at.isoformat(),
        "updated_at": payment.updated_at.isoformat(),
    }
