from __future__ import annotations

import asyncio

from app.domain.api_keys import ApiKeyService
from app.infrastructure.db import SessionLocal
from app.infrastructure.repositories.api_keys import SqlAlchemyApiKeyRepository


async def _main() -> None:
    async with SessionLocal() as session:
        repo = SqlAlchemyApiKeyRepository(session)
        service = ApiKeyService(repo)
        api_key, plaintext = await service.generate_key(
            org_id="org_dev",
            user_id="user_dev",
            name="dev key",
        )
        print("PLAINTEXT KEY (save this now):", plaintext)
        print("Preview:", api_key.preview)


if __name__ == "__main__":
    asyncio.run(_main())

