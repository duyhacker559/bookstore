"""
Payment Service Configuration
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    API_TITLE: str = "Bookstore Payment Service"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Database
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        'sqlite:///./payment_service.db'
    )
    
    # Stripe
    STRIPE_SECRET_KEY: str = os.getenv('STRIPE_SECRET_KEY', 'sk_test_demo')
    STRIPE_PUBLISHABLE_KEY: str = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_demo')
    
    # Authentication
    AUTH_TOKEN: str = os.getenv('PAYMENT_SERVICE_TOKEN', 'demo-token-123')
    MONOLITH_TOKEN: str = os.getenv('PAYMENT_SERVICE_TOKEN', 'demo-token-123')
    
    # Monolith Communication
    MONOLITH_URL: str = os.getenv(
        'MONOLITH_URL',
        'http://localhost:8000'
    )
    
    # RabbitMQ
    RABBITMQ_HOST: str = os.getenv('RABBITMQ_HOST', 'localhost')
    RABBITMQ_PORT: int = int(os.getenv('RABBITMQ_PORT', 5672))
    RABBITMQ_USER: str = os.getenv('RABBITMQ_USER', 'guest')
    RABBITMQ_PASSWORD: str = os.getenv('RABBITMQ_PASSWORD', 'guest')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    class Config:
        env_file = '.env'
        case_sensitive = False


@lru_cache()
def get_settings():
    """Get cached settings instance"""
    return Settings()
