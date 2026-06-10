from __future__ import annotations

import os
from typing import Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, EmailStr

app = FastAPI(title="User Service", version="1.0.0")
SERVICE_TOKEN = os.getenv("SERVICE_AUTH_TOKEN", "bookstore-internal-token")


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str


class User(BaseModel):
    id: int
    email: EmailStr
    full_name: str


USERS: Dict[int, User] = {
    1: User(id=1, email="alice@example.com", full_name="Alice Nguyen"),
    2: User(id=2, email="bob@example.com", full_name="Bob Tran"),
}


def _check_auth(authorization: Optional[str]) -> None:
    expected = f"Bearer {SERVICE_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def root() -> dict:
    return {"service": "user-service", "status": "running"}


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "user-service"}


@app.get("/api/users", response_model=list[User])
def list_users(authorization: Optional[str] = Header(default=None)) -> list[User]:
    _check_auth(authorization)
    return list(USERS.values())


@app.get("/api/users/{user_id}", response_model=User)
def get_user(user_id: int, authorization: Optional[str] = Header(default=None)) -> User:
    _check_auth(authorization)
    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/api/users", response_model=User, status_code=201)
def create_user(payload: UserCreate, authorization: Optional[str] = Header(default=None)) -> User:
    _check_auth(authorization)
    new_id = max(USERS.keys(), default=0) + 1
    user = User(id=new_id, email=payload.email, full_name=payload.full_name)
    USERS[new_id] = user
    return user
