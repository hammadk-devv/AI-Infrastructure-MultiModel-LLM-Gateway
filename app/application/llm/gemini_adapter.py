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


def _count_tokens_gemini(messages: list[LLMMessage]) -> int:
    """
    Gemini uses characters for pricing, but tokens for limits.
    Rough estimation: 1 token ~= 4 characters.
    """
    total_chars = sum(len(m.content) for m in messages)
    return max(1, total_chars // 4)


def _to_gemini_contents(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert unified messages into Gemini content format."""
    converted = []
    for m in messages:
        role = "user" if m.role in (MessageRole.USER, MessageRole.SYSTEM) else "model"
        converted.append({
            "role": role,
            "parts": [{"text": m.content}]
        })
    return converted


class GeminiAdapter(LLMProviderAdapter):
    """Google Gemini implementation of the LLMProviderAdapter protocol."""

    name = "gemini"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def acompletion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResult:
        contents = _to_gemini_contents(request.messages)
        
        # Gemini API Key is often passed as a query param
        url = f"models/{request.model}:generateContent?key={settings.gemini_api_key}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens or 2048,
            }
        }

        # Token estimation for metrics before request
        prompt_tokens = _count_tokens_gemini(request.messages)

        for attempt in range(3):
            try:
                with REQUEST_DURATION_SECONDS.labels(
                    provider=self.name,
                    model=request.model,
                ).time():
                    resp = await self._client.post(
                        url,
                        json=payload,
                        headers={"X-Request-ID": request.request_id},
                    )
                
                if resp.status_code == 429:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=True,
                        fallback=False,
                        message="Gemini rate limit exceeded",
                        status_code=429,
                    )
                
                if resp.status_code >= 500:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=True,
                        fallback=True,
                        message=f"Gemini server error: {resp.status_code}",
                        status_code=resp.status_code,
                    )
                
                if resp.status_code >= 400:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=False,
                        fallback=True,
                        message=f"Gemini client error: {resp.status_code} {resp.text}",
                        status_code=resp.status_code,
                    )

                data = resp.json()
                candidate = data["candidates"][0]
                content = candidate["content"]["parts"][0]["text"]
                finish_reason = candidate.get("finishReason")

                # Gemini provides usage metadata
                usage_metadata = data.get("usageMetadata", {})
                usage = LLMUsage(
                    prompt_tokens=usage_metadata.get("promptTokenCount", prompt_tokens),
                    completion_tokens=usage_metadata.get("candidatesTokenCount", 0),
                )

                REQUEST_TOTAL.labels(
                    provider=self.name,
                    model=request.model,
                    status="success",
                ).inc()
                
                # Metrics and cost estimation
                self._record_metrics(request.model, usage)

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
            except Exception as exc:
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
                        fallback=True,
                        message=f"Gemini unexpected error: {exc}",
                    ) from exc
                await asyncio.sleep(2**attempt)

        raise ProviderError(
            provider=self.name,
            model=request.model,
            retryable=True,
            fallback=True,
            message="Gemini retries exhausted",
        )

    async def astream(
        self,
        request: LLMCompletionRequest,
    ) -> AsyncIterator[LLMStreamChunk]:
        contents = _to_gemini_contents(request.messages)
        url = f"models/{request.model}:streamGenerateContent?key={settings.gemini_api_key}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens or 2048,
            }
        }

        prompt_tokens = _count_tokens_gemini(request.messages)
        completion_tokens = 0

        try:
            async with self._client.stream("POST", url, json=payload) as resp:
                if resp.status_code >= 400:
                    raise ProviderError(
                        provider=self.name,
                        model=request.model,
                        retryable=True,
                        fallback=True,
                        message=f"Gemini stream error: {resp.status_code}",
                        status_code=resp.status_code,
                    )

                async for line in resp.aiter_lines():
                    if not line or line.startswith("[") or line.startswith("]"):
                        continue
                    
                    # Gemini returns a JSON array of objects or individual objects
                    # depending on the stream format.
                    try:
                        clean_line = line.strip().rstrip(",")
                        if not clean_line: continue
                        data = json.loads(clean_line)
                        candidate = data["candidates"][0]
                        text_delta = candidate["content"]["parts"][0]["text"]
                        
                        completion_tokens += (len(text_delta) // 4) or 1
                        
                        yield LLMStreamChunk(
                            provider=self.name,
                            model=request.model,
                            delta=text_delta,
                            usage=None,
                            finish_reason=candidate.get("finishReason"),
                        )
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        except Exception as exc:
            raise ProviderError(
                provider=self.name,
                model=request.model,
                retryable=True,
                fallback=False,
                message=f"Gemini streaming error: {exc}",
            ) from exc
        finally:
             REQUEST_TOTAL.labels(
                provider=self.name,
                model=request.model,
                status="success",
            ).inc()

    def _record_metrics(self, model: str, usage: LLMUsage) -> None:
        TOKENS_TOTAL.labels(
            provider=self.name,
            model=model,
            type="prompt",
        ).inc(usage.prompt_tokens)
        TOKENS_TOTAL.labels(
            provider=self.name,
            model=model,
            type="completion",
        ).inc(usage.completion_tokens)
        
        # Estimate cost (very simplified)
        cost = (usage.prompt_tokens * 0.000125 / 1000) + (usage.completion_tokens * 0.000375 / 1000)
        COST_TOTAL.labels(provider=self.name, model=model).inc(cost)
