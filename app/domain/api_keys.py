from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Protocol

import bcrypt

from app.core.settings import get_settings


settings = get_settings()


@dataclass(frozen=True)
class ApiKeyPermissions:
    """Permissions and limits associated with an API key."""

    can_read: bool
    can_write: bool
    can_manage_keys: bool
    is_admin: bool
    rate_limit_per_minute: int


@dataclass(frozen=True)
class ApiKey:
    """Domain entity representing an API key (without storing plaintext).

    Args:
        id: Stable identifier for the key record.
        org_id: Organization that owns the key.
        user_id: User who created the key.
        name: Human-friendly name.
        key_hash: Stable SHA-256 hash used for lookup and caching.
        bcrypt_hash: Bcrypt hash of the full key for at-rest security.
        preview: First 8 characters of the key for display.
        expires_at: Optional expiration timestamp.
        last_used_at: Optional last-used timestamp.
        is_active: Whether the key is active.
        permissions: Permissions and rate limits associated with the key.
    """

    id: str
    org_id: str
    user_id: str
    name: str
    key_hash: str
    bcrypt_hash: str
    preview: str
    expires_at: datetime | None
    last_used_at: datetime | None
    is_active: bool
    permissions: ApiKeyPermissions


class ApiKeyRepository(Protocol):
    """Repository interface for API key persistence."""

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Return the API key matching the given lookup hash."""

    async def save(self, api_key: ApiKey) -> None:
        """Persist a new or updated ApiKey entity."""

    async def touch_last_used(self, api_key_id: str, when: datetime) -> None:
        """Update last_used_at for analytics and expiry."""


class ApiKeyService:
    """Service responsible for generating and validating API keys."""

    def __init__(self, repo: ApiKeyRepository) -> None:
        self._repo = repo

    async def generate_key(
        self,
        *,
        org_id: str,
        user_id: str,
        name: str,
        permissions: ApiKeyPermissions | None = None,
        ttl: timedelta | None = None,
    ) -> tuple[ApiKey, str]:
        """Generate a new API key and return (entity, plaintext_key).

        The plaintext key is returned once and must be shown to the user
        immediately; it is not stored in the database.
        """

        raw_suffix = secrets.token_urlsafe(32)
        prefix = settings.api_key_prefix
        plaintext_key = f"{prefix}{raw_suffix}"

        preview = plaintext_key[:8]
        key_hash = sha256(plaintext_key.encode("utf-8")).hexdigest()

        bcrypt_rounds = settings.api_key_bcrypt_rounds
        salt = bcrypt.gensalt(rounds=bcrypt_rounds)
        bcrypt_hash_bytes = bcrypt.hashpw(plaintext_key.encode("utf-8"), salt)
        bcrypt_hash = bcrypt_hash_bytes.decode("utf-8")

        now = datetime.now(timezone.utc)
        expires_at = now + ttl if ttl is not None else None

        effective_perms = permissions or ApiKeyPermissions(
            can_read=True,
            can_write=True,
            can_manage_keys=False,
            is_admin=False,
            rate_limit_per_minute=settings.rate_limit_requests_per_minute,
        )

        # Use secure random id if not provided by DB layer
        api_key_id = sha256(os.urandom(32)).hexdigest()

        entity = ApiKey(
            id=api_key_id,
            org_id=org_id,
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            bcrypt_hash=bcrypt_hash,
            preview=preview,
            expires_at=expires_at,
            last_used_at=None,
            is_active=True,
            permissions=effective_perms,
        )

        await self._repo.save(entity)
        return entity, plaintext_key

    async def authenticate(self, plaintext_key: str) -> ApiKey | None:
        """Validate a presented plaintext key and return its ApiKey entity.

        This method is primarily intended for cache warm-up or debugging.
        In the hot path, prefer lookup by key_hash using Redis.
        """

        key_hash = sha256(plaintext_key.encode("utf-8")).hexdigest()
        stored = await self._repo.get_by_hash(key_hash)
        if stored is None:
            return None

        if not stored.is_active:
            return None

        if stored.expires_at is not None and stored.expires_at < datetime.now(
            timezone.utc,
        ):
            return None

        bcrypt_valid = bcrypt.checkpw(
            plaintext_key.encode("utf-8"),
            stored.bcrypt_hash.encode("utf-8"),
        )
        if not bcrypt_valid:
            return None

        await self._repo.touch_last_used(stored.id, datetime.now(timezone.utc))
        return stored

