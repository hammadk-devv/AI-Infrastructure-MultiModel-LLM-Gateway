from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class MessageRole(str, Enum):
    """Supported chat message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(slots=True)
class LLMMessage:
    """Unified representation of a chat message."""

    role: MessageRole
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass(slots=True)
class LLMUsage:
    """Token usage for a completion."""

    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(slots=True)
class LLMCompletionRequest:
    """Domain-level completion request passed to provider adapters."""

    model: str
    messages: list[LLMMessage]
    temperature: float
    max_tokens: int | None
    tools: list[dict[str, Any]] | None
    tool_choice: str | dict[str, Any] | None
    request_id: str
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class LLMCompletionResult:
    """Normalized completion result from a provider."""

    provider: str
    model: str
    content: str
    usage: LLMUsage
    finish_reason: str | None
    raw_response: Mapping[str, Any]


@dataclass(slots=True)
class LLMStreamChunk:
    """Incremental streaming chunk."""

    provider: str
    model: str
    delta: str
    usage: LLMUsage | None
    finish_reason: str | None


class ProviderError(Exception):
    """Error raised by provider adapters with retry/fallback hints."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        retryable: bool,
        fallback: bool,
        message: str,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.retryable = retryable
        self.fallback = fallback
        self.status_code = status_code


class LLMProviderAdapter(Protocol):
    """Protocol implemented by all LLM provider adapters."""

    name: str

    async def acompletion(
        self,
        request: LLMCompletionRequest,
    ) -> LLMCompletionResult:
        """Execute a non-streaming completion request."""

    async def astream(
        self,
        request: LLMCompletionRequest,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Execute a streaming completion request."""

