"""Shipping API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from config import get_settings
from database import get_db
from models import Shipment, ShippingStatus
from schemas import (
    CreateShipmentRequest,
    CreateShipmentResponse,
    ShipmentStatusResponse,
    ShippingOption,
    UpdateShipmentStatusRequest,
    UpdateShipmentStatusResponse,
)
from services import EventPublisher, get_shipping_method, get_shipping_options

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1/shipping", tags=["shipping"])

publisher = EventPublisher(
    host=settings.RABBITMQ_HOST,
    port=settings.RABBITMQ_PORT,
    username=settings.RABBITMQ_USER,
    password=settings.RABBITMQ_PASSWORD,
)


def verify_auth(authorization: Optional[str] = Header(None)) -> bool:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    token = authorization[7:]
    if token not in [settings.AUTH_TOKEN, settings.MONOLITH_TOKEN]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return True


@router.get("/options", response_model=list[ShippingOption])
def list_shipping_options(
    weight: float = Query(1.0, ge=0),
    auth: bool = Depends(verify_auth),
):
    return get_shipping_options(weight)


@router.post("/create", response_model=CreateShipmentResponse)
def create_shipment(
    request: CreateShipmentRequest,
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_auth),
):
    existing = db.query(Shipment).filter(Shipment.order_id == request.order_id).first()
    if existing:
        return CreateShipmentResponse(
            shipment_id=existing.id,
            order_id=existing.order_id,
            status=existing.status.value,
            method_name=existing.method_name,
            fee=existing.fee,
            estimated_days=existing.estimated_days,
            address=existing.address,
        )

    try:
        method = get_shipping_method(request.method_code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    shipment = Shipment(
        order_id=request.order_id,
        address=request.address,
        method_code=request.method_code,
        method_name=method["name"],
        fee=request.fee,
        estimated_days=method["estimated_days"],
        status=ShippingStatus.PENDING,
    )
    db.add(shipment)
    db.commit()
    db.refresh(shipment)

    publisher.shipment_created(order_id=request.order_id, shipment_id=shipment.id, method_name=shipment.method_name)

    return CreateShipmentResponse(
        shipment_id=shipment.id,
        order_id=shipment.order_id,
        status=shipment.status.value,
        method_name=shipment.method_name,
        fee=shipment.fee,
        estimated_days=shipment.estimated_days,
        address=shipment.address,
    )


@router.get("/{order_id}", response_model=ShipmentStatusResponse)
def get_status(
    order_id: str,
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_auth),
):
    shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment not found for order {order_id}")

    return ShipmentStatusResponse(
        order_id=shipment.order_id,
        status=shipment.status.value,
        method_name=shipment.method_name,
        fee=shipment.fee,
        estimated_days=shipment.estimated_days,
        address=shipment.address,
    )


@router.put("/{order_id}", response_model=UpdateShipmentStatusResponse)
def update_status(
    order_id: str,
    request: UpdateShipmentStatusRequest,
    db: Session = Depends(get_db),
    auth: bool = Depends(verify_auth),
):
    shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment not found for order {order_id}")

    normalized_status = request.status.strip().lower()
    valid_statuses = {status.value: status for status in ShippingStatus}
    if normalized_status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid shipment status")

    previous_status = shipment.status.value
    shipment.status = valid_statuses[normalized_status]
    db.commit()
    db.refresh(shipment)

    if previous_status != shipment.status.value:
        publisher.shipment_updated(
            order_id=shipment.order_id,
            previous_status=previous_status,
            current_status=shipment.status.value,
        )

    return UpdateShipmentStatusResponse(
        order_id=shipment.order_id,
        previous_status=previous_status,
        current_status=shipment.status.value,
    )
