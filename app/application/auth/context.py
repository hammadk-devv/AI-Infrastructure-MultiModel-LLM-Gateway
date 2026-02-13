from __future__ import annotations

from dataclasses import dataclass

from app.domain.api_keys import ApiKey, ApiKeyPermissions


@dataclass(slots=True)
class AuthenticatedPrincipal:
    """Information about the authenticated caller derived from an API key."""

    api_key_id: str
    org_id: str
    user_id: str
    key_preview: str
    permissions: ApiKeyPermissions


@dataclass(slots=True)
class RequestContext:
    """Per-request context injected by the authentication middleware."""

    principal: AuthenticatedPrincipal
    client_ip: str


@dataclass(slots=True)
class CachedApiKey:
    """Minimal key information serialized into Redis."""

    id: str
    org_id: str
    user_id: str
    preview: str
    key_hash: str
    is_active: bool
    expires_at_ts: float | None
    permissions: ApiKeyPermissions

    @classmethod
    def from_entity(cls, api_key: ApiKey) -> "CachedApiKey":
        expires_at_ts = api_key.expires_at.timestamp() if api_key.expires_at else None
        return cls(
            id=api_key.id,
            org_id=api_key.org_id,
            user_id=api_key.user_id,
            preview=api_key.preview,
            key_hash=api_key.key_hash,
            is_active=api_key.is_active,
            expires_at_ts=expires_at_ts,
            permissions=api_key.permissions,
        )

