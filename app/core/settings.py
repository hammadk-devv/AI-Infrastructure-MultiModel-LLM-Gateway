from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Args:
        environment: Deployment environment, e.g. 'dev', 'staging', 'prod'.
        app_name: Human-readable application name.
        api_version: API version prefix.
        database_url: PostgreSQL DSN for the primary database.
        redis_url: Redis DSN for caching and rate limiting.
        sentry_dsn: Optional Sentry DSN for error reporting.
        enable_debug: Whether to enable debug features (never in prod).
        api_key_bcrypt_rounds: Bcrypt cost factor for API key hashing.
        api_key_prefix: Prefix for generated API keys.
        rate_limit_requests_per_minute: Default per-key rate limit.
    """

    environment: Literal["dev", "staging", "prod"] = Field(default="dev")
    app_name: str = Field(default="AI Infrastructure LLM Gateway")
    api_version: str = Field(default="v1")

    database_url: str = Field(default="sqlite+aiosqlite:///./gateway.db")
    redis_url: str = Field(default="memory://")

    sentry_dsn: str | None = None
    enable_debug: bool = Field(default=False)

    api_key_bcrypt_rounds: int = Field(default=12)
    api_key_prefix: str = Field(default="lkg_")

    # Default per-key rate limit (can be overridden per key)
    rate_limit_requests_per_minute: int = Field(default=1200)

    # Provider credentials and configuration
    openai_api_key: str | None = None
    openai_base_url: HttpUrl | None = None

    anthropic_api_key: str | None = None
    anthropic_base_url: HttpUrl | None = None

    gemini_api_key: str | None = None
    gemini_base_url: HttpUrl | None = None

    # Default HTTP timeouts (seconds)
    http_connect_timeout_s: float = Field(default=5.0)
    http_read_timeout_s: float = Field(default=30.0)
    http_write_timeout_s: float = Field(default=30.0)

    # Per-provider concurrency limits
    openai_max_concurrent: int = Field(default=100)
    anthropic_max_concurrent: int = Field(default=100)
    gemini_max_concurrent: int = Field(default=100)

    # CORS and Compliance
    allowed_origins: list[str] = Field(default=["*"])
    allowed_regions: list[str] | None = None

    # Model Registry settings
    model_registry_refresh_interval_s: int = Field(default=60)

    class Config:
        env_prefix = "LKG_"
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of Settings."""

    return Settings()  # type: ignore[call-arg]

