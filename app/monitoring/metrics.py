from __future__ import annotations

from prometheus_client import Counter, Histogram


REQUEST_TOTAL = Counter(
    "llm_gateway_requests_total",
    "Total number of LLM gateway requests",
    ["provider", "model", "status"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "llm_gateway_request_duration_seconds",
    "LLM gateway request duration in seconds",
    ["provider", "model"],
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0),
)

FIRST_TOKEN_DURATION_SECONDS = Histogram(
    "llm_gateway_first_token_duration_seconds",
    "Time to first token in seconds",
    ["provider"],
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0),
)

TOKENS_TOTAL = Counter(
    "llm_gateway_tokens_total",
    "Total tokens processed",
    ["provider", "model", "type"],
)

COST_TOTAL = Counter(
    "llm_gateway_cost_total",
    "Total cost in USD",
    ["provider", "model"],
)

CACHE_HITS_TOTAL = Counter(
    "llm_gateway_cache_hits_total",
    "Total cache hits",
    ["layer"],
)

CACHE_MISS_TOTAL = Counter(
    "llm_gateway_cache_miss_total",
    "Total cache misses",
    ["layer"],
)

RATE_LIMIT_HITS_TOTAL = Counter(
    "llm_gateway_rate_limit_hits_total",
    "Total rate limit violations",
)

CIRCUIT_BREAKER_STATE = Counter(
    "llm_gateway_circuit_breaker_state",
    "Circuit breaker state transitions",
    ["provider", "state"],
)

