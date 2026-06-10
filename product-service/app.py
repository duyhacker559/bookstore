from __future__ import annotations

import os
from typing import Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Product Service", version="1.0.0")
SERVICE_TOKEN = os.getenv("SERVICE_AUTH_TOKEN", "bookstore-internal-token")


class ProductCreate(BaseModel):
    name: str
    category: str
    price: float = Field(gt=0)


class Product(BaseModel):
    id: int
    name: str
    category: str
    price: float


PRODUCTS: Dict[int, Product] = {
    1: Product(id=1, name="Python 101", category="Books", price=19.9),
    2: Product(id=2, name="Noise Cancelling Headphones", category="Electronics", price=79.0),
}


def _check_auth(authorization: Optional[str]) -> None:
    expected = f"Bearer {SERVICE_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def root() -> dict:
    return {"service": "product-service", "status": "running"}


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "product-service"}


@app.get("/api/products", response_model=list[Product])
def list_products(authorization: Optional[str] = Header(default=None)) -> list[Product]:
    _check_auth(authorization)
    return list(PRODUCTS.values())


@app.get("/api/products/{product_id}", response_model=Product)
def get_product(product_id: int, authorization: Optional[str] = Header(default=None)) -> Product:
    _check_auth(authorization)
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.post("/api/products", response_model=Product, status_code=201)
def create_product(payload: ProductCreate, authorization: Optional[str] = Header(default=None)) -> Product:
    _check_auth(authorization)
    new_id = max(PRODUCTS.keys(), default=0) + 1
    product = Product(id=new_id, name=payload.name, category=payload.category, price=payload.price)
    PRODUCTS[new_id] = product
    return product
