from __future__ import annotations

import os
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Cart Service", version="1.0.0")
SERVICE_TOKEN = os.getenv("SERVICE_AUTH_TOKEN", "bookstore-internal-token")


class CartItemIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class CartItem(BaseModel):
    product_id: int
    quantity: int


CARTS: Dict[int, List[CartItem]] = defaultdict(list)


def _check_auth(authorization: Optional[str]) -> None:
    expected = f"Bearer {SERVICE_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def root() -> dict:
    return {"service": "cart-service", "status": "running"}


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "cart-service"}


@app.get("/api/carts/{user_id}", response_model=list[CartItem])
def get_cart(user_id: int, authorization: Optional[str] = Header(default=None)) -> list[CartItem]:
    _check_auth(authorization)
    return CARTS[user_id]


@app.post("/api/carts/{user_id}/items", response_model=list[CartItem])
def add_cart_item(user_id: int, payload: CartItemIn, authorization: Optional[str] = Header(default=None)) -> list[CartItem]:
    _check_auth(authorization)
    items = CARTS[user_id]
    for item in items:
        if item.product_id == payload.product_id:
            item.quantity += payload.quantity
            return items
    items.append(CartItem(product_id=payload.product_id, quantity=payload.quantity))
    return items


@app.delete("/api/carts/{user_id}/items/{product_id}", response_model=list[CartItem])
def remove_cart_item(user_id: int, product_id: int, authorization: Optional[str] = Header(default=None)) -> list[CartItem]:
    _check_auth(authorization)
    items = CARTS[user_id]
    CARTS[user_id] = [item for item in items if item.product_id != product_id]
    return CARTS[user_id]
