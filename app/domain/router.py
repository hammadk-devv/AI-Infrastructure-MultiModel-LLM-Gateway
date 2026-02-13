from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(slots=True)
class CircuitBreaker:
    """Simple sliding-window circuit breaker state."""

    provider: str
    failure_threshold: int = 5
    reset_timeout_s: int = 60

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at_ts: float | None = None

    def on_success(self) -> None:
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.opened_at_ts = None

    def on_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at_ts = time.time()

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            assert self.opened_at_ts is not None
            if time.time() - self.opened_at_ts >= self.reset_timeout_s:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        if self.state == CircuitState.HALF_OPEN:
            # Allow a single trial request in half-open.
            return True
        return False


@dataclass(slots=True)
class ProviderRouteConfig:
    """Mapping between logical model names and providers."""

    model: str
    provider: str
    provider_model: str
    priority: int = 0


@dataclass(slots=True)
class RouterCacheOptions:
    enabled: bool
    ttl_seconds: int


@dataclass(slots=True)
class RouterFallbackConfig:
    enabled: bool
    models: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RouterRequestMetadata:
    user_id: str
    org_id: str
    api_key_id: str
    request_id: str
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RouterDecision:
    """Final routing decision taken by the router."""

    provider: str
    provider_model: str
    logical_model: str
    from_cache: bool
    fallback_chain: list[str]

