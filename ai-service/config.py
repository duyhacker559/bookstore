from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "Bookstore AI Service"
    api_version: str = "v1"
    auth_token: str = "ai-service-token-123"

    data_path: str = "./data"
    checkpoint_path: str = "./data/lstm_checkpoint.pt"

    sequence_length: int = 5
    embedding_dim: int = 64
    lstm_hidden_dim: int = 96
    lstm_layers: int = 1
    recommendation_top_k: int = 5

    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_password"
    neo4j_database: str = "neo4j"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
