"""Shipping Service main application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from routes import router as shipping_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Microservice for shipping option and shipment management",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    init_db()
    logger.info("Shipping Service database initialized")


@app.get("/")
async def root() -> dict:
    return {"service": "shipping-service", "status": "running", "version": settings.API_VERSION}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "shipping-service", "version": settings.API_VERSION}


app.include_router(shipping_router)
