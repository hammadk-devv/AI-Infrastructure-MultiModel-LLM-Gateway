from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.api_keys import ApiKey, ApiKeyPermissions, ApiKeyRepository
from app.infrastructure.models import ApiKeyModel


class SqlAlchemyApiKeyRepository(ApiKeyRepository):
    """SQLAlchemy implementation of the ApiKeyRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None

        return self._to_domain(row)

    async def save(self, api_key: ApiKey) -> None:
        existing = await self._session.get(ApiKeyModel, api_key.id)
        if existing is None:
            model = ApiKeyModel(
                id=api_key.id,
                org_id=api_key.org_id,
                user_id=api_key.user_id,
                name=api_key.name,
                key_hash=api_key.key_hash,
                bcrypt_hash=api_key.bcrypt_hash,
                preview=api_key.preview,
                expires_at=api_key.expires_at,
                last_used_at=api_key.last_used_at,
                is_active=api_key.is_active,
                permissions=self._permissions_to_dict(api_key.permissions),
            )
            self._session.add(model)
        else:
            existing.org_id = api_key.org_id
            existing.user_id = api_key.user_id
            existing.name = api_key.name
            existing.key_hash = api_key.key_hash
            existing.bcrypt_hash = api_key.bcrypt_hash
            existing.preview = api_key.preview
            existing.expires_at = api_key.expires_at
            existing.last_used_at = api_key.last_used_at
            existing.is_active = api_key.is_active
            existing.permissions = self._permissions_to_dict(api_key.permissions)

        await self._session.commit()

    async def touch_last_used(self, api_key_id: str, when: datetime) -> None:
        await self._session.execute(
            update(ApiKeyModel)
            .where(ApiKeyModel.id == api_key_id)
            .values(last_used_at=when),
        )
        await self._session.commit()

    async def list_all(self) -> list[ApiKey]:
        stmt = select(ApiKeyModel).order_by(ApiKeyModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_domain(row) for row in result.scalars().all()]

    @staticmethod
    def _permissions_to_dict(perms: ApiKeyPermissions) -> dict[str, Any]:
        return {
            "can_read": perms.can_read,
            "can_write": perms.can_write,
            "can_manage_keys": perms.can_manage_keys,
            "is_admin": perms.is_admin,
            "rate_limit_per_minute": perms.rate_limit_per_minute,
        }

    @staticmethod
    def _permissions_from_dict(data: dict[str, Any]) -> ApiKeyPermissions:
        return ApiKeyPermissions(
            can_read=bool(data.get("can_read", True)),
            can_write=bool(data.get("can_write", True)),
            can_manage_keys=bool(data.get("can_manage_keys", False)),
            is_admin=bool(data.get("is_admin", data.get("isAdmin", False))),
            rate_limit_per_minute=int(
                data.get("rate_limit_per_minute", 0),
            ),
        )

    def _to_domain(self, model: ApiKeyModel) -> ApiKey:
        perms = self._permissions_from_dict(model.permissions)
        return ApiKey(
            id=model.id,
            org_id=model.org_id,
            user_id=model.user_id,
            name=model.name,
            key_hash=model.key_hash,
            bcrypt_hash=model.bcrypt_hash,
            preview=model.preview,
            expires_at=model.expires_at,
            last_used_at=model.last_used_at,
            is_active=model.is_active,
            permissions=perms,
        )

