from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from redis.asyncio import Redis

from app.application.auth.context import RequestContext
from app.application.llm.factory import ProviderAdapterFactory
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.domain.adapters import (
    LLMCompletionRequest,
    LLMCompletionResult,
    LLMProviderAdapter,
    ProviderError,
)
from app.domain.models import ModelConfig
from app.domain.router import (
    CircuitBreaker,
    RouterCacheOptions,
    RouterDecision,
    RouterFallbackConfig,
    RouterRequestMetadata,
)
from app.domain.services.model_registry import ModelRegistry
from app.monitoring.metrics import (
    CACHE_HITS_TOTAL,
    CACHE_MISS_TOTAL,
    CIRCUIT_BREAKER_STATE,
)

logger = get_logger(__name__)
settings = get_settings()


class ModelRouterService:
    """Core model routing service with circuit breakers and caching."""

    def __init__(
        self,
        redis: Redis,
        registry: ModelRegistry,
        factory: ProviderAdapterFactory,
    ) -> None:
        self._redis = redis
        self._registry = registry
        self._factory = factory
        
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    def _get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        if provider not in self._circuit_breakers:
            self._circuit_breakers[provider] = CircuitBreaker(provider=provider)
        return self._circuit_breakers[provider]

    def _get_semaphore(self, provider: str) -> asyncio.Semaphore:
        if provider not in self._semaphores:
            # Default to settings or reasonable limit
            limit = getattr(settings, f"{provider}_max_concurrent", 100)
            self._semaphores[provider] = asyncio.Semaphore(limit)
        return self._semaphores[provider]

    async def chat_completion(
        self,
        *,
        llm_request: LLMCompletionRequest,
        cache: RouterCacheOptions,
        fallback: RouterFallbackConfig,
        metadata: RouterRequestMetadata,
        streaming: bool,
    ) -> tuple[RouterDecision, LLMCompletionResult | None, Mapping[str, Any] | None]:
        """Route a non-streaming completion request and optionally use cache."""

        cache_key = (
            self._build_cache_key(llm_request, metadata)
            if cache.enabled and not streaming
            else None
        )

        if cache_key:
            cached = await self._get_cache(cache_key)
            if cached is not None:
                CACHE_HITS_TOTAL.labels(layer="response").inc()
                decision = RouterDecision(
                    provider=cached["provider"],
                    provider_model=cached["model"],
                    logical_model=llm_request.model,
                    from_cache=True,
                    fallback_chain=[],
                )
                return decision, None, cached
            CACHE_MISS_TOTAL.labels(layer="response").inc()

        # Resolve primary model
        cfg = await self._registry.get_model(llm_request.model)
        if not cfg:
            raise ValueError(f"Model not found or inactive: {llm_request.model}")

        models_chain: list[ModelConfig] = [cfg]
        if fallback.enabled:
            fallbacks = await self._registry.get_fallback_chain(f"{cfg.provider}:{cfg.model_name}")
            # Filter fallbacks if a specific list was requested
            if fallback.models:
                requested = set(fallback.models)
                fallbacks = [m for m in fallbacks if m.model_name in requested]
            models_chain.extend(fallbacks)

        last_error: Exception | None = None
        tried_models: list[str] = []

        for model_cfg in models_chain:
            logical_model = model_cfg.model_name
            tried_models.append(logical_model)
            
            provider = model_cfg.provider
            adapter = self._factory.get_adapter(provider)
            
            cb = self._get_circuit_breaker(provider)
            if not cb.allow_request():
                CIRCUIT_BREAKER_STATE.labels(
                    provider=provider,
                    state="open",
                ).inc()
                continue

            semaphore = self._get_semaphore(provider)

            try:
                async with semaphore:
                    adjusted_request = LLMCompletionRequest(
                        model=model_cfg.model_name,
                        messages=llm_request.messages,
                        temperature=llm_request.temperature,
                        max_tokens=llm_request.max_tokens,
                        tools=llm_request.tools,
                        tool_choice=llm_request.tool_choice,
                        request_id=llm_request.request_id,
                        metadata=llm_request.metadata,
                    )
                    
                    if streaming:
                        decision = RouterDecision(
                            provider=provider,
                            provider_model=model_cfg.model_name,
                            logical_model=llm_request.model,
                            from_cache=False,
                            fallback_chain=[m.model_name for m in models_chain[1:]],
                        )
                        return decision, None, None

                    result = await adapter.acompletion(adjusted_request)
                    cb.on_success()

                    decision = RouterDecision(
                        provider=provider,
                        provider_model=model_cfg.model_name,
                        logical_model=llm_request.model,
                        from_cache=False,
                        fallback_chain=[m.model_name for m in models_chain[1:]],
                    )

                    if cache_key:
                        await self._set_cache(
                            cache_key,
                            {
                                "provider": result.provider,
                                "model": result.model,
                                "content": result.content,
                                "usage": {
                                    "prompt_tokens": result.usage.prompt_tokens,
                                    "completion_tokens": result.usage.completion_tokens,
                                },
                                "finish_reason": result.finish_reason,
                            },
                            ttl_seconds=cache.ttl_seconds,
                        )

                    return decision, result, None
            except ProviderError as exc:
                last_error = exc
                cb.on_failure()
                if not exc.fallback:
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                cb.on_failure()

        logger.error(
            "All provider candidates failed",
            extra={
                "lkg_extra": json.dumps(
                    {
                        "models_chain": [m.model_name for m in models_chain],
                        "tried_models": tried_models,
                        "user_id": metadata.user_id,
                        "org_id": metadata.org_id,
                        "api_key_id": metadata.api_key_id,
                        "request_id": metadata.request_id,
                        "error": str(last_error),
                    },
                ),
            },
        )
        raise RuntimeError("All provider candidates failed") from last_error

    @staticmethod
    def _build_cache_key(
        llm_request: LLMCompletionRequest,
        metadata: RouterRequestMetadata,
    ) -> str:
        payload = {
            "model": llm_request.model,
            "messages": [
                {"role": m.role.value, "content": m.content}
                for m in llm_request.messages
            ],
            "temperature": llm_request.temperature,
            "max_tokens": llm_request.max_tokens,
            "user_id": metadata.user_id,
            "org_id": metadata.org_id,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = sha256(raw.encode("utf-8")).hexdigest()
        return f"lkg:resp:{digest}"

    async def _get_cache(self, key: str) -> Mapping[str, Any] | None:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def _set_cache(
        self,
        key: str,
        value: Mapping[str, Any],
        *,
        ttl_seconds: int,
    ) -> None:
        await self._redis.set(key, json.dumps(value), ex=ttl_seconds)

