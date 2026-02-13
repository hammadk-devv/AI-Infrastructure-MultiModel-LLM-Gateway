from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis

from app.api.dependencies import (
    get_model_router,
    get_provider_factory,
    get_request_context,
)
from app.application.auth.context import RequestContext
from app.application.llm.factory import ProviderAdapterFactory
from app.application.services.model_router import ModelRouterService
from app.core.logging import get_logger
from app.domain.adapters import LLMCompletionRequest, LLMMessage, MessageRole
from app.domain.router import (
    RouterCacheOptions,
    RouterFallbackConfig,
    RouterRequestMetadata,
)


router = APIRouter(prefix="/v1", tags=["chat"])
logger = get_logger(__name__)


@dataclass(slots=True)
class ChatFallbackConfig:
    enabled: bool
    models: list[str]


@dataclass(slots=True)
class ChatCacheConfig:
    enabled: bool
    ttl: int


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: Request,
    body: dict[str, Any],
    ctx: RequestContext = Depends(get_request_context),
    router_service: ModelRouterService = Depends(get_model_router),
    factory: ProviderAdapterFactory = Depends(get_provider_factory),
) -> StreamingResponse | JSONResponse:
    started_ns = time.perf_counter_ns()
    request_id = body.get("request_id") or str(uuid4())

    model = str(body.get("model") or "gpt-4o")
    raw_messages = body.get("messages") or []
    stream = bool(body.get("stream") or False)
    temperature = float(body.get("temperature") or 0.7)
    max_tokens_val = body.get("max_tokens")
    max_tokens = int(max_tokens_val) if max_tokens_val is not None else None
    tools = body.get("tools") or None

    fallback_spec = body.get("fallback") or {}
    fallback_cfg = ChatFallbackConfig(
        enabled=bool(fallback_spec.get("enabled", False)),
        models=list(fallback_spec.get("models") or []),
    )

    cache_spec = body.get("cache") or {}
    cache_cfg = ChatCacheConfig(
        enabled=bool(cache_spec.get("enabled", False)),
        ttl=int(cache_spec.get("ttl") or 3600),
    )

    metadata = body.get("metadata") or {}
    tags = list(metadata.get("tags") or [])
    conversation_id = metadata.get("conversation_id")

    messages: list[LLMMessage] = []
    for m in raw_messages:
        role = MessageRole(m.get("role", "user"))
        content = str(m.get("content") or "")
        messages.append(
            LLMMessage(
                role=role,
                content=content,
            ),
        )

    llm_request = LLMCompletionRequest(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice=body.get("tool_choice"),
        request_id=request_id,
        metadata=metadata,
    )

    router_cache = RouterCacheOptions(enabled=cache_cfg.enabled, ttl_seconds=cache_cfg.ttl)
    router_fallback = RouterFallbackConfig(
        enabled=fallback_cfg.enabled,
        models=fallback_cfg.models,
    )
    router_metadata = RouterRequestMetadata(
        user_id=ctx.principal.user_id,
        org_id=ctx.principal.org_id,
        api_key_id=ctx.principal.api_key_id,
        request_id=request_id,
        tags=tags,
        extra={"conversation_id": conversation_id},
    )

    decision, result, cached_payload = await router_service.chat_completion(
        llm_request=llm_request,
        cache=router_cache,
        fallback=router_fallback,
        metadata=router_metadata,
        streaming=stream,
    )

    rate_limit_info = getattr(request.state, "rate_limit_info", None) or {}
    limit = int(rate_limit_info.get("limit") or 0)
    remaining = int(rate_limit_info.get("remaining") or 0)
    reset_ts = int(rate_limit_info.get("reset_ts") or int(time.time()))

    headers = {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_ts),
        "X-Provider": decision.provider,
        "X-Model": decision.provider_model,
        "X-Cache": "HIT" if decision.from_cache else "MISS",
        "X-Auth-Cache": "HIT"
        if getattr(request.state, "auth_cache_hit", False)
        else "MISS",
        "X-Request-ID": request_id,
    }

    duration_ms = (time.perf_counter_ns() - started_ns) / 1_000_000
    logger.info(
        "chat.completions",
        extra={
            "lkg_extra": json.dumps(
                {
                    "request_id": request_id,
                    "api_key_preview": ctx.principal.key_preview,
                    "user_id": ctx.principal.user_id,
                    "organization_id": ctx.principal.org_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": 200,
                    "duration_ms": duration_ms,
                    "provider": decision.provider,
                    "model": decision.provider_model,
                    "prompt_tokens": result.usage.prompt_tokens
                    if result
                    else cached_payload["usage"]["prompt_tokens"],
                    "completion_tokens": result.usage.completion_tokens
                    if result
                    else cached_payload["usage"]["completion_tokens"],
                    "total_tokens": result.usage.total_tokens
                    if result
                    else cached_payload["usage"]["prompt_tokens"]
                    + cached_payload["usage"]["completion_tokens"],
                    "cache_hit": decision.from_cache,
                    "rate_limited": False,
                    "error": None,
                },
            ),
        },
    )

    if stream:
        # Streaming path: re-invoke the provider adapter based on the routing decision.
        adapter = factory.get_adapter(decision.provider)

        async def stream_iter():
            async for chunk in adapter.astream(llm_request):
                data = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "choices": [
                        {
                            "delta": {"content": chunk.delta},
                            "finish_reason": chunk.finish_reason,
                        },
                    ],
                }
                yield json.dumps(data) + "\n"

        return StreamingResponse(stream_iter(), media_type="application/json", headers=headers)

    if decision.from_cache and cached_payload is not None:
        resp_body = {
            "id": request_id,
            "object": "chat.completion",
            "model": decision.logical_model,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": cached_payload["content"],
                    },
                    "finish_reason": cached_payload.get("finish_reason"),
                    "index": 0,
                },
            ],
            "usage": cached_payload["usage"],
        }
    else:
        assert result is not None
        resp_body = {
            "id": request_id,
            "object": "chat.completion",
            "model": decision.logical_model,
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": result.content,
                    },
                    "finish_reason": result.finish_reason,
                    "index": 0,
                },
            ],
            "usage": {
                "prompt_tokens": result.usage.prompt_tokens,
                "completion_tokens": result.usage.completion_tokens,
                "total_tokens": result.usage.total_tokens,
            },
        }

    return JSONResponse(content=resp_body, headers=headers)

