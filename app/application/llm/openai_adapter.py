from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import tiktoken

from app.core.settings import get_settings
from app.domain.adapters import (
    LLMCompletionRequest,
    LLMCompletionResult,
    LLMMessage,
    LLMStreamChunk,
    LLMUsage,
    LLMProviderAdapter,
    MessageRole,
    ProviderError,
)
from app.monitoring.metrics import (
    REQUEST_DURATION_SECONDS,
    REQUEST_TOTAL,
    TOKENS_TOTAL,
    COST_TOTAL,
)


settings = get_settings()

_ENCODING_CACHE: dict[str, tiktoken.Encoding] = {}




def _encoding_for_model(model: str) -> tiktoken.Encoding:
    if model in _ENCODING_CACHE:
        return _ENCODING_CACHE[model]
    encoding = tiktoken.encoding_for_model(model)
    _ENCODING_CACHE[model] = encoding
    return encoding


def _count_tokens(model: str, messages: list[LLMMessage]) -> int:
    encoding = _encoding_for_model(model)
    text_parts: list[str] = []
    for m in messages:
        text_parts.append(m.role.value)
        text_parts.append(m.content)
    joined = "\n".join(text_parts)
    return len(encoding.encode(joined))


_MODEL_COSTS_USD: dict[str, dict[str, float]] = {
    # Example values; should be kept in sync with provider pricing.
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
}


def _estimate_cost(model: str, usage: LLMUsage) -> float:
    cfg = _MODEL_COSTS_USD.get(model)
    if not cfg:
        return 0.0
    prompt_cost = cfg["prompt"] * (usage.prompt_tokens / 1000)
    completion_cost = cfg["completion"] * (usage.completion_tokens / 1000)
    return prompt_cost + completion_cost


def _to_openai_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for m in messages:
        item: dict[str, Any] = {
            "role": m.role.value,
            "content": m.content,
        }
        if m.name:
            item["name"] = m.name
        if m.tool_calls:
            item["tool_calls"] = m.tool_calls
        result.append(item)
    return result


class OpenAIAdapter(LLMProviderAdapter):
    """OpenAI implementation of the LLMProviderAdapter protocol."""

    name = "openai"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def acompletion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResult:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": _to_openai_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice

        prompt_tokens = _count_tokens(request.model, request.messages)

        for attempt in range(3):
            try:
                with REQUEST_DURATION_SECONDS.labels(
                    provider=self.name,
                    model=request.model,
                ).time():
                    resp = await self._client.post(
                        "chat/completions",
                        content=json.dumps(payload),
                        headers={"X-Request-ID": request.request_id},
                    )
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=True,
                        fallback=False,
                        message=f"OpenAI transient error: {resp.status_code} {resp.text}",
                        status_code=resp.status_code,
                    )
                if resp.status_code >= 400:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=False,
                        fallback=True,
                        message=f"OpenAI client error: {resp.status_code} {resp.text}",
                        status_code=resp.status_code,
                    )

                data = resp.json()
                choice = data["choices"][0]
                message = choice["message"]
                content = message.get("content") or ""
                finish_reason = choice.get("finish_reason")

                # Prefer provider's token counts if present.
                usage_data = data.get("usage") or {}
                completion_tokens = int(usage_data.get("completion_tokens") or 0)
                if completion_tokens == 0:
                    completion_tokens = _count_tokens(
                        request.model,
                        [
                            LLMMessage(
                                role=MessageRole.ASSISTANT,
                                content=content,
                            ),
                        ],
                    )
                usage = LLMUsage(
                    prompt_tokens=int(usage_data.get("prompt_tokens") or prompt_tokens),
                    completion_tokens=completion_tokens,
                )

                REQUEST_TOTAL.labels(
                    provider=self.name,
                    model=request.model,
                    status="success",
                ).inc()
                TOKENS_TOTAL.labels(
                    provider=self.name,
                    model=request.model,
                    type="prompt",
                ).inc(usage.prompt_tokens)
                TOKENS_TOTAL.labels(
                    provider=self.name,
                    model=request.model,
                    type="completion",
                ).inc(usage.completion_tokens)
                COST_TOTAL.labels(
                    provider=self.name,
                    model=request.model,
                ).inc(_estimate_cost(request.model, usage))

                return LLMCompletionResult(
                    provider=self.name,
                    model=request.model,
                    content=content,
                    usage=usage,
                    finish_reason=finish_reason,
                    raw_response=data,
                )
            except ProviderError:
                if attempt == 2:
                    REQUEST_TOTAL.labels(
                        provider=self.name,
                        model=request.model,
                        status="error",
                    ).inc()
                    raise
                await asyncio.sleep(2**attempt)
            except httpx.RequestError as exc:  # network or timeout
                if attempt == 2:
                    REQUEST_TOTAL.labels(
                        provider=self.name,
                        model=request.model,
                        status="error",
                    ).inc()
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=True,
                        fallback=False,
                        message=f"OpenAI network error: {exc}",
                    ) from exc
                await asyncio.sleep(2**attempt)

        raise ProviderError(
            provider=self.name,
            model=request.model,
            retryable=True,
            fallback=True,
            message="OpenAI retries exhausted",
        )

    async def astream(
        self,
        request: LLMCompletionRequest,
    ) -> AsyncIterator[LLMStreamChunk]:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": _to_openai_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        if request.tools:
            payload["tools"] = request.tools
        if request.tool_choice:
            payload["tool_choice"] = request.tool_choice

        prompt_tokens = _count_tokens(request.model, request.messages)
        completion_tokens = 0

        try:
            async with self._client.stream(
                "POST",
                "chat/completions",
                content=json.dumps(payload),
                headers={"X-Request-ID": request.request_id},
            ) as resp:
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=True,
                        fallback=False,
                        message=f"OpenAI transient error: {resp.status_code}",
                        status_code=resp.status_code,
                    )
                if resp.status_code >= 400:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=False,
                        fallback=True,
                        message=f"OpenAI client error: {resp.status_code}",
                        status_code=resp.status_code,
                    )

                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:") :].strip()
                    if data_str == "[DONE]":
                        break
                    data = json.loads(data_str)
                    choice = data["choices"][0]
                    delta = choice.get("delta") or {}
                    text_delta = delta.get("content") or ""
                    if not text_delta:
                        continue
                    completion_tokens += _count_tokens(
                        request.model,
                        [
                            LLMMessage(
                                role=MessageRole.ASSISTANT,
                                content=text_delta,
                            ),
                        ],
                    )
                    usage = LLMUsage(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    )
                    yield LLMStreamChunk(
                        provider=self.name,
                        model=request.model,
                        delta=text_delta,
                        usage=None,
                        finish_reason=None,
                    )

        except httpx.RequestError as exc:
            raise ProviderError(
                provider=self.name,
                model=request.model,
                retryable=True,
                fallback=False,
                message=f"OpenAI network error during stream: {exc}",
            ) from exc
        finally:
            usage = LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            REQUEST_TOTAL.labels(
                provider=self.name,
                model=request.model,
                status="success",
            ).inc()
            TOKENS_TOTAL.labels(
                provider=self.name,
                model=request.model,
                type="prompt",
            ).inc(usage.prompt_tokens)
            TOKENS_TOTAL.labels(
                provider=self.name,
                model=request.model,
                type="completion",
            ).inc(usage.completion_tokens)
            COST_TOTAL.labels(
                provider=self.name,
                model=request.model,
            ).inc(_estimate_cost(request.model, usage))

