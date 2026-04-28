import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_TITLE: str = "Bookstore AI Behavior Service"
    API_VERSION: str = "1.0.0"
    AUTH_TOKEN: str = os.getenv("AI_BEHAVIOR_SERVICE_TOKEN", "ai-behavior-service-token-123")
    DB_PATH: str = os.getenv("AI_BEHAVIOR_DB_PATH", "./data/behavior_events.db")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_API_VERSION: str = os.getenv("GEMINI_API_VERSION", "v1beta")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
