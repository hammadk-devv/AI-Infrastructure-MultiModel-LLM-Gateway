from __future__ import annotations

from collections.abc import AsyncIterator

import redis.asyncio as redis

from app.core.settings import get_settings


settings = get_settings()

if settings.redis_url != "memory://":
    redis_pool = redis.ConnectionPool.from_url(
        str(settings.redis_url),
        max_connections=50,
        decode_responses=False,
    )
else:
    redis_pool = None


def get_redis_client() -> redis.Redis:
    """Return a pooled async Redis client."""

    return redis.Redis(connection_pool=redis_pool)


async def get_redis_dependency() -> AsyncIterator[redis.Redis]:
    """FastAPI dependency that yields a Redis client."""

    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()

