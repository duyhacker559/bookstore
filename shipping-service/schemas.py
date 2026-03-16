"""API schemas for Shipping Service."""

from pydantic import BaseModel, Field


class ShippingOption(BaseModel):
    code: str
    name: str
    fee: float
    estimated_days: int


class CreateShipmentRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    address: str = Field(..., min_length=3)
    method_code: str = Field(..., min_length=1)
    fee: float = Field(..., ge=0)


class CreateShipmentResponse(BaseModel):
    shipment_id: int
    order_id: str
    status: str
    method_name: str
    fee: float
    estimated_days: int
    address: str


class ShipmentStatusResponse(BaseModel):
    order_id: str
    status: str
    method_name: str
    fee: float
    estimated_days: int
    address: str


class UpdateShipmentStatusRequest(BaseModel):
    status: str = Field(..., min_length=1)


class UpdateShipmentStatusResponse(BaseModel):
    order_id: str
    previous_status: str
    current_status: str
