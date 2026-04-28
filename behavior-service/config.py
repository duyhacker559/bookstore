import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_TITLE: str = "Bookstore Behavior Service"
    API_VERSION: str = "1.0.0"
    AUTH_TOKEN: str = os.getenv("BEHAVIOR_SERVICE_TOKEN", "behavior-service-token-123")
    TRAIN_DATA_PATH: str = os.getenv("BEHAVIOR_TRAIN_DATA_PATH", "./data/vi_behavior_lexicon.json")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
