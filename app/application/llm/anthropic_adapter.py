from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.settings import get_settings
from app.domain.adapters import (
    LLMCompletionRequest,
    LLMCompletionResult,
    LLMMessage,
    LLMProviderAdapter,
    LLMStreamChunk,
    LLMUsage,
    MessageRole,
    ProviderError,
)
from app.monitoring.metrics import (
    COST_TOTAL,
    REQUEST_DURATION_SECONDS,
    REQUEST_TOTAL,
    TOKENS_TOTAL,
)


settings = get_settings()




def _count_tokens_estimate(messages: list[LLMMessage]) -> int:
    # Placeholder estimate: ~4 chars per token; replace with anthropic tokenizer for production.
    total_chars = sum(len(m.content) for m in messages)
    return max(1, total_chars // 4)


_ANTHROPIC_COSTS_USD: dict[str, dict[str, float]] = {
    # Example pricing for Claude 3 models (USD per 1K tokens).
    "claude-3-5-sonnet-latest": {"prompt": 0.003, "completion": 0.015},
    "claude-3-opus-latest": {"prompt": 0.015, "completion": 0.075},
    "claude-3-haiku-latest": {"prompt": 0.0008, "completion": 0.004},
}


def _estimate_cost(model: str, usage: LLMUsage) -> float:
    cfg = _ANTHROPIC_COSTS_USD.get(model)
    if not cfg:
        return 0.0
    prompt_cost = cfg["prompt"] * (usage.prompt_tokens / 1000)
    completion_cost = cfg["completion"] * (usage.completion_tokens / 1000)
    return prompt_cost + completion_cost


def _to_anthropic_messages(messages: list[LLMMessage]) -> tuple[list[dict[str, Any]], str | None]:
    """Convert unified messages into Anthropic roles and system prompt."""

    system_parts: list[str] = []
    converted: list[dict[str, Any]] = []

    for m in messages:
        if m.role == MessageRole.SYSTEM:
            system_parts.append(m.content)
            continue
        if m.role == MessageRole.USER:
            role = "user"
        elif m.role == MessageRole.ASSISTANT:
            role = "assistant"
        else:
            role = "user"

        converted.append(
            {
                "role": role,
                "content": m.content,
            },
        )

    system_prompt = "\n".join(system_parts) if system_parts else None
    return converted, system_prompt


class AnthropicAdapter(LLMProviderAdapter):
    """Anthropic implementation of the LLMProviderAdapter protocol."""

    name = "anthropic"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def acompletion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResult:
        messages, system_prompt = _to_anthropic_messages(request.messages)

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1024,
            "temperature": request.temperature,
        }
        if system_prompt:
            payload["system"] = system_prompt

        prompt_tokens = _count_tokens_estimate(request.messages)

        for attempt in range(3):
            try:
                with REQUEST_DURATION_SECONDS.labels(
                    provider=self.name,
                    model=request.model,
                ).time():
                    resp = await self._client.post(
                        "messages",
                        content=json.dumps(payload),
                        headers={"X-Request-ID": request.request_id},
                    )
                if resp.status_code in (429, 500, 502, 503, 504, 529):
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=True,
                        fallback=False,
                        message=f"Anthropic transient error: {resp.status_code} {resp.text}",
                        status_code=resp.status_code,
                    )
                if resp.status_code >= 400:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=False,
                        fallback=True,
                        message=f"Anthropic client error: {resp.status_code} {resp.text}",
                        status_code=resp.status_code,
                    )

                data = resp.json()
                content_blocks = data.get("content", [])
                text_parts: list[str] = []
                for block in content_blocks:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text") or "")
                content = "".join(text_parts)

                usage_data = data.get("usage") or {}
                completion_tokens = int(usage_data.get("output_tokens") or 0)
                if completion_tokens == 0:
                    completion_tokens = _count_tokens_estimate(
                        [
                            LLMMessage(
                                role=MessageRole.ASSISTANT,
                                content=content,
                            ),
                        ],
                    )

                usage = LLMUsage(
                    prompt_tokens=int(
                        usage_data.get("input_tokens") or prompt_tokens,
                    ),
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
                    finish_reason=None,
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
            except httpx.RequestError as exc:
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
                        message=f"Anthropic network error: {exc}",
                    ) from exc
                await asyncio.sleep(2**attempt)

        raise ProviderError(
            provider=self.name,
            model=request.model,
            retryable=True,
            fallback=True,
            message="Anthropic retries exhausted",
        )

    async def astream(
        self,
        request: LLMCompletionRequest,
    ) -> AsyncIterator[LLMStreamChunk]:
        messages, system_prompt = _to_anthropic_messages(request.messages)

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1024,
            "temperature": request.temperature,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        prompt_tokens = _count_tokens_estimate(request.messages)
        completion_tokens = 0

        try:
            async with self._client.stream(
                "POST",
                "messages",
                content=json.dumps(payload),
                headers={"X-Request-ID": request.request_id},
            ) as resp:
                if resp.status_code in (429, 500, 502, 503, 504, 529):
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=True,
                        fallback=False,
                        message=f"Anthropic transient error: {resp.status_code}",
                        status_code=resp.status_code,
                    )
                if resp.status_code >= 400:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=False,
                        fallback=True,
                        message=f"Anthropic client error: {resp.status_code}",
                        status_code=resp.status_code,
                    )

                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:") :].strip()
                    if data_str == "[DONE]":
                        break
                    event = json.loads(data_str)
                    if event.get("type") != "content_block_delta":
                        continue
                    delta = event.get("delta") or {}
                    if delta.get("type") != "text_delta":
                        continue
                    text_delta = delta.get("text") or ""
                    if not text_delta:
                        continue

                    completion_tokens += _count_tokens_estimate(
                        [
                            LLMMessage(
                                role=MessageRole.ASSISTANT,
                                content=text_delta,
                            ),
                        ],
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
                message=f"Anthropic network error during stream: {exc}",
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

