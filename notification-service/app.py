"""Notification Service main application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from services.event_consumer import EventConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Microservice for sending order and shipment notifications",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event consumer instance
event_consumer = None


@app.on_event("startup")
async def startup_event() -> None:
    global event_consumer
    init_db()
    logger.info("Notification Service database initialized")

    # Start event consumer
    event_consumer = EventConsumer()
    event_consumer.start()
    logger.info("Event consumer started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    if event_consumer:
        event_consumer.stop()
    logger.info("Notification Service shutting down")


@app.get("/")
async def root() -> dict:
    return {"service": "notification-service", "status": "running", "version": settings.API_VERSION}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "notification-service", "version": settings.API_VERSION}
