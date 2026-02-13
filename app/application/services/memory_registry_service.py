from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import ModelCapability, ModelConfig
from app.domain.services.model_registry import ModelRegistry
from app.infrastructure.models import ModelConfigModel


class InMemoryModelRegistry(ModelRegistry):
    """In-memory implementation of ModelRegistry for portable mode."""

    def __init__(
        self,
        session_factory: Any,
        refresh_interval_s: int = 60,
    ) -> None:
        self._session_factory = session_factory
        self._refresh_interval_s = refresh_interval_s
        self._models: dict[str, ModelConfig] = {}
        self._lock = asyncio.Lock()
        self._last_refresh: datetime | None = None
        self._refresh_task: asyncio.Task | None = None
        self._is_running = False

    async def start(self) -> None:
        """Start background refresh."""
        if self._is_running:
            return
        self._is_running = True
        await self.refresh()
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        from app.core.logging import get_logger
        get_logger(__name__).info("InMemoryModelRegistry background refresh started.")

    async def stop(self) -> None:
        """Stop background refresh."""
        self._is_running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        from app.core.logging import get_logger
        get_logger(__name__).info("InMemoryModelRegistry background refresh stopped.")

    async def get_model(self, model_identifier: str) -> ModelConfig | None:
        async with self._lock:
            return self._models.get(model_identifier)

    async def list_models(
        self,
        *,
        provider: str | None = None,
        capability: ModelCapability | None = None,
        active_only: bool = True,
    ) -> list[ModelConfig]:
        async with self._lock:
            results = list(self._models.values())

        if active_only:
            results = [m for m in results if m.is_active]
        if provider:
            results = [m for m in results if m.provider == provider]
        if capability:
            results = [m for m in results if capability in m.capabilities]

        return sorted(results, key=lambda x: x.priority, reverse=True)

    async def get_fallback_chain(self, failed_model: str) -> list[ModelConfig]:
        # Simple fallback: same provider, active, ordered by priority
        base_model = await self.get_model(failed_model)
        if not base_model:
            return []

        all_active = await self.list_models(active_only=True)
        return [
            m for m in all_active 
            if m.provider == base_model.provider and m.model_name != base_model.model_name
        ]

    async def _refresh_loop(self) -> None:
        while self._is_running:
            try:
                await asyncio.sleep(self._refresh_interval_s)
                await self.refresh()
            except asyncio.CancelledError:
                break
            except Exception:
                from app.core.logging import get_logger
                get_logger(__name__).exception("Error during model registry refresh")

    async def refresh(self) -> None:
        """Load models from database into memory."""
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        
        async with self._session_factory() as session:
            stmt = select(ModelConfigModel).where(ModelConfigModel.is_active == True)
            result = await session.execute(stmt)
            orm_models = result.scalars().all()

            new_models = {}
            for orm in orm_models:
                capabilities_raw = orm.capabilities
                if isinstance(capabilities_raw, str):
                    import json
                    capabilities_list = json.loads(capabilities_raw)
                else:
                    capabilities_list = capabilities_raw

                config = ModelConfig(
                    id=orm.id,
                    provider=orm.provider,
                    model_name=orm.model_name,
                    display_name=orm.display_name,
                    context_window=orm.context_window,
                    max_output_tokens=orm.max_output_tokens,
                    capabilities=[ModelCapability(c) for c in capabilities_list],
                    cost_per_1k_input=float(orm.cost_per_1k_input),
                    cost_per_1k_output=float(orm.cost_per_1k_output),
                    is_active=orm.is_active,
                    priority=orm.priority,
                    created_at=orm.created_at,
                    updated_at=orm.updated_at,
                )
                new_models[config.model_name] = config
                # Also index by display name/alias if needed
                new_models[config.display_name] = config

            async with self._lock:
                self._models = new_models
                self._last_refresh = datetime.now(timezone.utc)
            
            logger.info(f"Refreshed {len(orm_models)} models in memory registry.")
