from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Mapping

import msgpack
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import ModelCapability, ModelConfig
from app.domain.services.model_registry import ModelRegistry
from app.infrastructure.models import ModelConfigModel

logger = logging.getLogger(__name__)


class RedisModelRegistry(ModelRegistry):
    """
    Redis-backed implementation of ModelRegistry with background refresh.
    
    Cache Structure:
    - Hash 'lkg:models:active': { provider:name -> msgpack_data }
    - Hash 'lkg:models:aliases': { alias -> provider:name }
    - Set 'lkg:models:capability:{cap}': { provider:name }
    """

    def __init__(
        self,
        redis: Redis,
        session_factory: async_sessionmaker[AsyncSession],
        refresh_interval_s: int = 60,
    ) -> None:
        self._redis = redis
        self._session_factory = session_factory
        self._refresh_interval_s = refresh_interval_s
        self._refresh_task: asyncio.Task | None = None
        self._is_running = False

    async def start(self) -> None:
        """Start the background refresh task."""
        if self._is_running:
            return
        self._is_running = True
        # Perform initial refresh before starting the background task
        await self.refresh()
        self._refresh_task = asyncio.create_task(self._refresh_loop())
        logger.info("RedisModelRegistry background refresh started.")

    async def stop(self) -> None:
        """Stop the background refresh task."""
        self._is_running = False
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
        logger.info("RedisModelRegistry background refresh stopped.")

    async def _refresh_loop(self) -> None:
        while self._is_running:
            try:
                await asyncio.sleep(self._refresh_interval_s)
                await self.refresh()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error during model registry refresh")

    async def get_model(self, model_identifier: str) -> ModelConfig | None:
        # 1. Resolve alias if necessary
        # Identifier can be 'gpt-4' or 'openai:gpt-4'
        if ":" not in model_identifier:
            # Check aliases hash
            actual_key = await self._redis.hget("lkg:models:aliases", model_identifier)
            if actual_key:
                model_key = actual_key.decode("utf-8")
            else:
                # Try as direct model name (finding first provider that has it)
                # In production, we should probably enforce provider:model or unique names
                model_key = model_identifier 
        else:
            model_key = model_identifier

        # 2. Get from active models hash
        raw = await self._redis.hget("lkg:models:active", model_key)
        if not raw:
            return None

        return self._unpack_model_config(raw)

    async def list_models(
        self,
        *,
        provider: str | None = None,
        capability: ModelCapability | None = None,
        active_only: bool = True,
    ) -> list[ModelConfig]:
        if capability:
            # Get model keys from capability set
            keys = await self._redis.smembers(f"lkg:models:capability:{capability.value}")
            if not keys:
                return []
            # Fetch all from active hash
            model_keys = [k.decode("utf-8") for k in keys]
            raw_list = await self._redis.hmget("lkg:models:active", model_keys)
        else:
            # Get everything from active hash
            raw_map = await self._redis.hgetall("lkg:models:active")
            raw_list = raw_map.values()

        models: list[ModelConfig] = []
        for raw in raw_list:
            if raw:
                model = self._unpack_model_config(raw)
                if provider and model.provider != provider:
                    continue
                models.append(model)
        
        return sorted(models, key=lambda m: m.priority)

    async def get_fallback_chain(self, failed_model: str) -> list[ModelConfig]:
        # Simple policy: find models with same provider or highest priority
        all_models = await self.list_models()
        # Filter out the failed model
        return [m for m in all_models if f"{m.provider}:{m.model_name}" != failed_model]

    async def refresh(self) -> None:
        """Sync DB to Redis with zero cache stampede protection."""
        # Simple implementation: query all and overwrite
        async with self._session_factory() as session:
            stmt = select(ModelConfigModel).where(ModelConfigModel.is_active == True)
            result = await session.execute(stmt)
            db_models = result.scalars().all()

        if not db_models:
            logger.warning("No active models found in DB during refresh")
            return

        active_hash = {}
        alias_hash = {}
        capability_sets: dict[str, list[str]] = {}
        for m in db_models:
            full_name = f"{m.provider}:{m.model_name}"
            # Entity mapping
            capabilities_raw = m.capabilities
            if isinstance(capabilities_raw, str):
                import json
                capabilities_list = json.loads(capabilities_raw)
            else:
                capabilities_list = capabilities_raw

            config = ModelConfig(
                id=m.id,
                provider=m.provider,
                model_name=m.model_name,
                display_name=m.display_name,
                context_window=m.context_window,
                max_output_tokens=m.max_output_tokens,
                capabilities=[ModelCapability(c) for c in capabilities_list],
                cost_per_1k_input=float(m.cost_per_1k_input),
                cost_per_1k_output=float(m.cost_per_1k_output),
                is_active=m.is_active,
                priority=m.priority,
            )
            packed = self._pack_model_config(config)
            active_hash[full_name] = packed
            
            # Simple alias: model name itself if unique? 
            # Or dedicated alias field in DB? For now use model_name
            alias_hash[m.model_name] = full_name
            
            for cap in config.capabilities:
                capability_sets.setdefault(cap.value, []).append(full_name)

        # Atomic-ish update using pipeline
        async with self._redis.pipeline() as pipe:
            pipe.delete("lkg:models:active", "lkg:models:aliases")
            for cap_val in capability_sets:
                pipe.delete(f"lkg:models:capability:{cap_val}")
            
            pipe.hset("lkg:models:active", mapping=active_hash)
            pipe.hset("lkg:models:aliases", mapping=alias_hash)
            for cap_val, keys in capability_sets.items():
                pipe.sadd(f"lkg:models:capability:{cap_val}", *keys)
            
            await pipe.execute()
        
        logger.info(f"Refreshed {len(db_models)} models in registry.")

    def _pack_model_config(self, m: ModelConfig) -> bytes:
        data = {
            "id": str(m.id),
            "provider": m.provider,
            "model_name": m.model_name,
            "display_name": m.display_name,
            "context_window": m.context_window,
            "max_output_tokens": m.max_output_tokens,
            "capabilities": [c.value for c in m.capabilities],
            "cost_per_1k_input": m.cost_per_1k_input,
            "cost_per_1k_output": m.cost_per_1k_output,
            "is_active": m.is_active,
            "priority": m.priority,
        }
        return msgpack.packb(data)

    def _unpack_model_config(self, raw: bytes) -> ModelConfig:
        data = msgpack.unpackb(raw, raw=False)
        return ModelConfig(
            id=data["id"],
            provider=data["provider"],
            model_name=data["model_name"],
            display_name=data["display_name"],
            context_window=data["context_window"],
            max_output_tokens=data["max_output_tokens"],
            capabilities=[ModelCapability(c) for c in data["capabilities"]],
            cost_per_1k_input=data["cost_per_1k_input"],
            cost_per_1k_output=data["cost_per_1k_output"],
            is_active=data["is_active"],
            priority=data["priority"],
        )
