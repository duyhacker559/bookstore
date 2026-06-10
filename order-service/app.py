from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Order Service", version="1.0.0")
SERVICE_TOKEN = os.getenv("SERVICE_AUTH_TOKEN", "bookstore-internal-token")


class OrderCreate(BaseModel):
    user_id: int = Field(gt=0)
    total_amount: float = Field(gt=0)


class OrderStatusUpdate(BaseModel):
    status: str


class Order(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: str
    created_at: str


ORDERS: Dict[int, Order] = {}


def _check_auth(authorization: Optional[str]) -> None:
    expected = f"Bearer {SERVICE_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def root() -> dict:
    return {"service": "order-service", "status": "running"}


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "order-service"}


@app.get("/api/orders", response_model=list[Order])
def list_orders(authorization: Optional[str] = Header(default=None)) -> list[Order]:
    _check_auth(authorization)
    return list(ORDERS.values())


@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: int, authorization: Optional[str] = Header(default=None)) -> Order:
    _check_auth(authorization)
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.post("/api/orders", response_model=Order, status_code=201)
def create_order(payload: OrderCreate, authorization: Optional[str] = Header(default=None)) -> Order:
    _check_auth(authorization)
    new_id = max(ORDERS.keys(), default=0) + 1
    order = Order(
        id=new_id,
        user_id=payload.user_id,
        total_amount=payload.total_amount,
        status="pending",
        created_at=datetime.utcnow().isoformat() + "Z",
    )
    ORDERS[new_id] = order
    return order


@app.post("/api/orders/{order_id}/status", response_model=Order)
def update_order_status(order_id: int, payload: OrderStatusUpdate, authorization: Optional[str] = Header(default=None)) -> Order:
    _check_auth(authorization)
    order = ORDERS.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    ORDERS[order_id] = order
    return order
