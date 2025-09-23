"""Application configuration settings."""

from __future__ import annotations

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration sourced from environment variables or `.env` files."""

    app_env: str = Field(default="development", description="Deployment environment name.")
    log_level: str = Field(default="INFO", description="Minimum logging level for the app.")
    api_root_url: AnyHttpUrl = Field(
        default="http://localhost:8000",
        description="Public root URL of the API service.",
    )
    database_url: str = Field(
        default="postgresql+psycopg2://USER:PASSWORD@localhost:5432/eveindy",
        description="SQLAlchemy connection string for Postgres.",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL for caches/queues."
    )

    # Provider rate limits (token bucket): capacity (tokens) and refill rate (tokens/sec)
    esi_capacity: float = Field(default=10.0, description="ESI token bucket capacity")
    esi_refill_rate: float = Field(default=2.0, description="ESI tokens per second")
    adam4eve_capacity: float = Field(default=1.0, description="Adam4EVE polite capacity")
    adam4eve_refill_rate: float = Field(default=0.1, description="Adam4EVE tokens per sec (~10s)")
    fuzzwork_capacity: float = Field(default=1.0, description="Fuzzwork capacity")
    fuzzwork_refill_rate: float = Field(default=0.2, description="Fuzzwork tokens per sec (~5s)")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


__all__ = ["Settings"]
