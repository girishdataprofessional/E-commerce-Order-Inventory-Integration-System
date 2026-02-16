"""
App configuration — reads from env vars / .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://fulfil_user:fulfil_pass@postgres:5432/fulfil_erp"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # Webhook (placeholder for production HMAC verification)
    SHOPIFY_WEBHOOK_SECRET: str = "dev-secret-key-change-in-production"

    # Inventory
    LOW_STOCK_THRESHOLD: int = 10
    INVENTORY_SYNC_INTERVAL_SECONDS: int = 300

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
