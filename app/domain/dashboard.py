from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MetricsSummary(BaseModel):
    """Aggregated metrics for a time period."""
    period: Dict[str, str] = Field(..., description="Start and end timestamps")
    tokens: Dict[str, int] = Field(..., description="Total, prompt, and completion tokens")
    cost: Dict[str, float] = Field(..., description="Total cost and breakdown by provider")
    requests: Dict[str, int] = Field(..., description="Total, success, and error counts")
    latency: Dict[str, float] = Field(..., description="P50, P95, P99 latencies in ms")
    cache: Dict[str, Any] = Field(..., description="Cache hits, misses, and ratio")


class TimeSeriesPoint(BaseModel):
    """Single point in a time series."""
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    tokens: int = Field(default=0)
    cost: float = Field(default=0.0)
    requests: int = Field(default=0)
    latency: float = Field(default=0.0)
    errors: int = Field(default=0)


class ModelPerformance(BaseModel):
    """Performance metrics for a specific model."""
    model_id: str
    model_name: str
    provider: str
    requests: int = Field(default=0)
    success_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    avg_latency: float = Field(default=0.0, description="Average latency in ms")
    p95_latency: float = Field(default=0.0, description="95th percentile latency in ms")
    total_tokens: int = Field(default=0)
    total_cost: float = Field(default=0.0)


class Alert(BaseModel):
    """System alert or notification."""
    id: str
    severity: str = Field(..., description="critical, high, medium, or low")
    title: str
    description: str
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    acknowledged: bool = Field(default=False)
    resolved: bool = Field(default=False)
    metadata: Optional[Dict[str, Any]] = None


class CostBreakdown(BaseModel):
    """Cost analysis by provider, model, or organization."""
    period: Dict[str, str]
    by_provider: Dict[str, float] = Field(default_factory=dict)
    by_model: Dict[str, float] = Field(default_factory=dict)
    by_organization: Dict[str, float] = Field(default_factory=dict)
    total: float = Field(default=0.0)


class UsageStats(BaseModel):
    """Token usage statistics."""
    period: Dict[str, str]
    total_tokens: int = Field(default=0)
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    by_model: Dict[str, int] = Field(default_factory=dict)
    trend: Optional[str] = Field(None, description="up, down, or stable")
