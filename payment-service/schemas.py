"""
Pydantic schemas for Payment Service API
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class PaymentRequest(BaseModel):
    """Payment processing request"""
    
    order_id: str = Field(..., description="Order ID from monolith")
    amount: float = Field(..., gt=0, description="Amount in dollars")
    currency: str = Field(default="USD", description="Currency code")
    customer_email: EmailStr = Field(..., description="Customer email")
    payment_method_id: str = Field(..., description="Stripe payment method ID or token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "order-123",
                "amount": 99.99,
                "currency": "USD",
                "customer_email": "customer@example.com",
                "payment_method_id": "tok_visa"
            }
        }


class PaymentResponse(BaseModel):
    """Successful payment response"""
    
    status: str = Field(..., description="Payment status (succeeded, processing, etc)")
    payment_id: str = Field(..., description="Stripe charge/payment ID")
    order_id: str = Field(..., description="Associated order ID")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    transaction_id: Optional[str] = Field(None, description="Stripe transaction ID")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "succeeded",
                "payment_id": "ch_1234567890",
                "order_id": "order-123",
                "amount": 99.99,
                "currency": "USD",
                "transaction_id": "txn_456",
                "message": "Payment processed successfully"
            }
        }


class PaymentErrorResponse(BaseModel):
    """Error response"""
    
    status: str = Field(..., description="Error status")
    error: str = Field(..., description="Error message")
    order_id: Optional[str] = Field(None, description="Associated order ID")
    code: Optional[str] = Field(None, description="Error code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "failed",
                "error": "Card declined",
                "order_id": "order-123",
                "code": "card_declined"
            }
        }


class RefundRequest(BaseModel):
    """Refund request"""
    
    payment_id: str = Field(..., description="Stripe payment/charge ID")
    amount: Optional[float] = Field(None, gt=0, description="Amount to refund (optional, full refund if omitted)")
    reason: Optional[str] = Field(None, description="Reason for refund")
    
    class Config:
        json_schema_extra = {
            "example": {
                "payment_id": "ch_1234567890",
                "amount": 50.00,
                "reason": "Customer request"
            }
        }


class RefundResponse(BaseModel):
    """Refund response"""
    
    status: str = Field(..., description="Refund status")
    refund_id: str = Field(..., description="Stripe refund ID")
    payment_id: str = Field(..., description="Original payment/charge ID")
    amount: float = Field(..., description="Refunded amount")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "succeeded",
                "refund_id": "re_1234567890",
                "payment_id": "ch_1234567890",
                "amount": 50.00,
                "message": "Refund processed successfully"
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response"""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2026-03-09T12:00:00"
            }
        }
