from __future__ import annotations

import httpx

from app.application.llm.anthropic_adapter import AnthropicAdapter
from app.application.llm.gemini_adapter import GeminiAdapter
from app.application.llm.openai_adapter import OpenAIAdapter
from app.core.settings import get_settings
from app.domain.adapters import LLMProviderAdapter

settings = get_settings()


class ProviderAdapterFactory:
    """Factory for creating and pooling LLM provider adapters and their HTTP clients."""

    def __init__(self) -> None:
        self._clients: dict[str, httpx.AsyncClient] = {}
        self._adapters: dict[str, LLMProviderAdapter] = {}

    def get_adapter(self, provider: str) -> LLMProviderAdapter:
        """Get or create an adapter for the specified provider."""
        provider = provider.lower()
        if provider not in self._adapters:
            client = self._get_or_create_client(provider)
            if provider == "openai":
                self._adapters[provider] = OpenAIAdapter(client)
            elif provider == "anthropic":
                self._adapters[provider] = AnthropicAdapter(client)
            elif provider == "gemini":
                self._adapters[provider] = GeminiAdapter(client)
            else:
                raise ValueError(f"Unknown provider: {provider}")

        return self._adapters[provider]

    def _get_or_create_client(self, provider: str) -> httpx.AsyncClient:
        if provider not in self._clients:
            if provider == "openai":
                base_url = str(settings.openai_base_url or "https://api.openai.com/v1/")
                self._clients[provider] = httpx.AsyncClient(
                    base_url=base_url,
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=httpx.Timeout(
                        timeout=settings.http_read_timeout_s,
                        connect=settings.http_connect_timeout_s,
                    ),
                    limits=httpx.Limits(
                        max_connections=settings.openai_max_concurrent,
                        max_keepalive_connections=settings.openai_max_concurrent,
                    ),
                )
            elif provider == "anthropic":
                base_url = str(settings.anthropic_base_url or "https://api.anthropic.com/v1/")
                self._clients[provider] = httpx.AsyncClient(
                    base_url=base_url,
                    headers={
                        "x-api-key": settings.anthropic_api_key or "",
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    timeout=httpx.Timeout(
                        timeout=settings.http_read_timeout_s,
                        connect=settings.http_connect_timeout_s,
                    ),
                    limits=httpx.Limits(
                        max_connections=settings.anthropic_max_concurrent,
                        max_keepalive_connections=settings.anthropic_max_concurrent,
                    ),
                )
            elif provider == "gemini":
                base_url = str(settings.gemini_base_url or "https://generativelanguage.googleapis.com/v1beta/")
                self._clients[provider] = httpx.AsyncClient(
                    base_url=base_url,
                    headers={
                        "Content-Type": "application/json",
                    },
                    timeout=httpx.Timeout(
                        timeout=settings.http_read_timeout_s,
                        connect=settings.http_connect_timeout_s,
                    ),
                    limits=httpx.Limits(
                        max_connections=settings.gemini_max_concurrent,
                        max_keepalive_connections=settings.gemini_max_concurrent,
                    ),
                )
        return self._clients[provider]

    async def shutdown(self) -> None:
        """Close all HTTP clients."""
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
        self._adapters.clear()
