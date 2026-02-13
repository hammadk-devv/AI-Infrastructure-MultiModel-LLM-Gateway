from __future__ import annotations

import time
from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable

import msgpack
from fastapi import HTTPException, Request
from fastapi.responses import Response
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.application.auth.context import (
    AuthenticatedPrincipal,
    CachedApiKey,
    RequestContext,
)
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.domain.api_keys import ApiKeyService
from app.infrastructure.db import SessionLocal
from app.infrastructure.memory_client import get_memory_redis
from app.infrastructure.redis_client import get_redis_client
from app.infrastructure.repositories.api_keys import SqlAlchemyApiKeyRepository


logger = get_logger(__name__)
settings = get_settings()


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Authenticate requests using API keys with Redis-backed caching and rate limits."""

    def __init__(self, app: Callable, redis_client: Redis | None = None) -> None:
        super().__init__(app)
        if redis_client:
            self._redis_client = redis_client
        elif settings.redis_url == "memory://":
            self._redis_client = get_memory_redis()
        else:
            self._redis_client = get_redis_client()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path in (
            "/",
            "/internal/health",
            "/internal/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ):
            return await call_next(request)

        api_key = self._extract_api_key(request)
        if api_key is None:
            logger.warning(f"Missing API key for request to {request.url.path}")
            raise HTTPException(status_code=401, detail="Missing API key")

        api_key = api_key.strip()
        lookup_hash = sha256(api_key.encode("utf-8")).hexdigest()
        logger.info(f"Authenticating request to {request.url.path} with key hash: {lookup_hash[:12]}...")

        start_ns = time.perf_counter_ns()
        cached, cache_hit = await self._get_cached_key(lookup_hash)
        cache_duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000

        if cached is None:
            principal = await self._authenticate_via_db(api_key, lookup_hash)
        else:
            principal = self._principal_from_cached(cached)

        client_ip = request.client.host if request.client else "unknown"

        allowed, remaining, reset_ts = await self._check_rate_limit(
            lookup_hash=lookup_hash,
            client_ip=client_ip,
            limit_per_minute=principal.permissions.rate_limit_per_minute,
        )
        if not allowed:
            logger.warning(
                "Rate limit exceeded",
                extra={"lkg_extra": f'{{"api_key_id": "{principal.api_key_id}"}}'},
            )
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        request.state.request_context = RequestContext(
            principal=principal,
            client_ip=client_ip,
        )

        request.state.auth_cache_hit = cache_hit
        request.state.rate_limit_info = {
            "limit": principal.permissions.rate_limit_per_minute,
            "remaining": max(0, remaining),
            "reset_ts": reset_ts,
        }

        response = await call_next(request)
        response.headers["X-Auth-Cache-Latency-ms"] = f"{cache_duration_ms:.2f}"
        return response

    @staticmethod
    def _extract_api_key(request: Request) -> str | None:
        header_val = request.headers.get("x-api-key")
        if header_val:
            return header_val.strip()

        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        return None

    async def _get_cached_key(self, lookup_hash: str) -> tuple[CachedApiKey | None, bool]:
        key = f"lkg:auth:apikey:{lookup_hash}"
        raw = await self._redis_client.get(key)
        if raw is None:
            return None, False
        data = msgpack.unpackb(raw, raw=False)
        from app.domain.api_keys import ApiKeyPermissions
        permissions = ApiKeyPermissions(**data["permissions"])
        cached = CachedApiKey(
            id=data["id"],
            org_id=data["org_id"],
            user_id=data["user_id"],
            preview=data["preview"],
            key_hash=data["key_hash"],
            is_active=bool(data["is_active"]),
            expires_at_ts=data["expires_at_ts"],
            permissions=permissions,
        )
        if cached.expires_at_ts is not None and cached.expires_at_ts < time.time():
            # Key expired; let DB perform final check and refresh cache.
            return None, False
        return cached, True

    async def _authenticate_via_db(
        self,
        api_key: str,
        lookup_hash: str,
    ) -> AuthenticatedPrincipal:
        async with SessionLocal() as session:
            repo = SqlAlchemyApiKeyRepository(session)
            service = ApiKeyService(repo)
            try:
                entity = await service.authenticate(api_key)
            except Exception as e:
                logger.error(f"Error authenticating via DB: {e}", exc_info=True)
                raise
            if entity is None:
                raise HTTPException(status_code=401, detail="Invalid API key")

        cached = CachedApiKey.from_entity(entity)
        await self._cache_key(cached)
        return self._principal_from_cached(cached)

    async def _cache_key(self, cached: CachedApiKey) -> None:
        key = f"lkg:auth:apikey:{cached.key_hash}"
        from dataclasses import asdict
        payload = {
            "id": cached.id,
            "org_id": cached.org_id,
            "user_id": cached.user_id,
            "preview": cached.preview,
            "key_hash": cached.key_hash,
            "is_active": cached.is_active,
            "expires_at_ts": cached.expires_at_ts,
            "permissions": asdict(cached.permissions),
        }
        ttl_seconds = 300
        if cached.expires_at_ts is not None:
            seconds_until_expiry = int(cached.expires_at_ts - time.time())
            if seconds_until_expiry <= 0:
                return
            ttl_seconds = min(ttl_seconds, seconds_until_expiry)
        await self._redis_client.set(key, msgpack.packb(payload), ex=ttl_seconds)

    @staticmethod
    def _principal_from_cached(cached: CachedApiKey) -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            api_key_id=cached.id,
            org_id=cached.org_id,
            user_id=cached.user_id,
            key_preview=cached.preview,
            permissions=cached.permissions,
        )

    async def _check_rate_limit(
        self,
        *,
        lookup_hash: str,
        client_ip: str,
        limit_per_minute: int,
    ) -> tuple[bool, int, int]:
        window_seconds = 60
        now = int(time.time())
        redis_key = f"lkg:ratelimit:{lookup_hash}:{client_ip}"
        current = await self._redis_client.incr(redis_key)
        if current == 1:
            await self._redis_client.expire(redis_key, window_seconds)
        ttl = await self._redis_client.ttl(redis_key)
        reset_ts = now + (ttl if ttl > 0 else window_seconds)
        remaining = max(0, limit_per_minute - current)
        return current <= limit_per_minute, remaining, reset_ts

