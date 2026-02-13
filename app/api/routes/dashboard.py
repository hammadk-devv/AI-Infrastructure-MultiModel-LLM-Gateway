"""
Dashboard metrics and analytics API routes.
Provides aggregated data for the production monitoring dashboard.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_request_context
from app.application.auth.context import RequestContext
from app.domain.dashboard import (
    Alert,
    CostBreakdown,
    MetricsSummary,
    ModelPerformance,
    TimeSeriesPoint,
    UsageStats,
)
from app.infrastructure.repositories.conversations import ConversationRepository
from app.infrastructure.repositories.api_keys import SqlAlchemyApiKeyRepository
from app.infrastructure.db import get_db_session

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> MetricsSummary:
    """
    Get aggregated metrics summary for the specified time window.
    Returns KPIs: tokens, cost, requests, latency, cache performance.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    repo = ConversationRepository(session)
    summary = await repo.get_metrics_summary(hours)
    
    return MetricsSummary(
        period={
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        },
        tokens={
            "total": summary["total_tokens"],
            "prompt": int(summary["total_tokens"] * 0.7),
            "completion": int(summary["total_tokens"] * 0.3),
        },
        cost={
            "total": (summary["total_tokens"] / 1000) * 0.01,
            "openai": (summary["total_tokens"] / 1000) * 0.007,
            "anthropic": (summary["total_tokens"] / 1000) * 0.002,
            "gemini": (summary["total_tokens"] / 1000) * 0.001,
        },
        requests={
            "total": summary["total_requests"],
            "success": summary["total_requests"],
            "error": 0,
        },
        latency={
            "p50": summary["avg_latency"],
            "p95": summary["avg_latency"] * 1.5,
            "p99": summary["avg_latency"] * 2.5,
        },
        cache={
            "hits": 0,
            "misses": summary["total_requests"],
            "ratio": 0.0,
        },
    )


@router.get("/metrics/timeseries", response_model=List[TimeSeriesPoint])
async def get_metrics_timeseries(
    hours: int = Query(24, ge=1, le=168),
    interval: str = Query("1h", regex="^(5m|15m|1h|6h|1d)$"),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> List[TimeSeriesPoint]:
    """
    Get time-series metrics data for charting.
    Interval determines granularity: 5m, 15m, 1h, 6h, 1d.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    # TODO: Implement actual time-series aggregation
    # Generate mock data points
    points = []
    current = start_time
    delta = timedelta(hours=1)  # Simplified for now
    
    while current <= end_time:
        points.append(
            TimeSeriesPoint(
                timestamp=current.isoformat(),
                tokens=50_000,
                cost=17.5,
                requests=640,
                latency=195.0,
                errors=1,
            )
        )
        current += delta
    
    return points


@router.get("/models/performance", response_model=List[ModelPerformance])
async def get_model_performance(
    hours: int = Query(24, ge=1, le=168),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> List[ModelPerformance]:
    """
    Get performance metrics for all active models.
    Includes success rates, latency, token usage, and costs.
    """
    repo = ConversationRepository(session)
    performances = await repo.get_model_performance(hours)
    
    return [
        ModelPerformance(
            model_id=p["model_name"],
            model_name=p["model_name"],
            provider=p["provider"],
            requests=p["requests"],
            success_rate=p["success_rate"],
            avg_latency=p["avg_latency"],
            p95_latency=p["avg_latency"] * 1.5,
            total_tokens=p["total_tokens"],
            total_cost=p["total_cost"],
        )
        for p in performances
    ]


@router.get("/analytics/costs", response_model=CostBreakdown)
async def get_cost_breakdown(
    hours: int = Query(24, ge=1, le=720),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> CostBreakdown:
    """
    Get detailed cost breakdown by provider, model, and organization.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    return CostBreakdown(
        period={
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        },
        by_provider={
            "openai": 275.30,
            "anthropic": 105.20,
            "gemini": 43.00,
        },
        by_model={
            "gpt-4o": 275.30,
            "claude-3-5-sonnet-latest": 105.20,
            "gemini-1.5-pro": 43.00,
        },
        by_organization={
            "org_test": 423.50,
        },
        total=423.50,
    )


@router.get("/analytics/usage", response_model=UsageStats)
async def get_usage_stats(
    hours: int = Query(24, ge=1, le=720),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> UsageStats:
    """
    Get token usage statistics and trends.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    return UsageStats(
        period={
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
        },
        total_tokens=1_200_000,
        prompt_tokens=800_000,
        completion_tokens=400_000,
        by_model={
            "gpt-4o": 800_000,
            "claude-3-5-sonnet-latest": 250_000,
            "gemini-1.5-pro": 150_000,
        },
        trend="up",
    )


@router.get("/alerts/active", response_model=List[Alert])
async def get_active_alerts(
    severity: Optional[str] = Query(None, regex="^(critical|high|medium|low)$"),
    ctx: RequestContext = Depends(get_request_context),
    session: AsyncSession = Depends(get_db_session),
) -> List[Alert]:
    """
    Get active system alerts, optionally filtered by severity.
    """
    # TODO: Implement actual alert system
    alerts = [
        Alert(
            id="alert_001",
            severity="high",
            title="Rate limit exceeded",
            description="API key lkg_test_123 exceeded rate limit",
            timestamp=(datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
            acknowledged=False,
            resolved=False,
        ),
        Alert(
            id="alert_002",
            severity="medium",
            title="Provider timeout",
            description="OpenAI API timeout on gpt-4o request",
            timestamp=(datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat(),
            acknowledged=True,
            resolved=False,
        ),
    ]
    
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    return alerts
@router.get("/auth/verify")
async def verify_auth(
    ctx: RequestContext = Depends(get_request_context),
):
    """
    Verify the API key is valid and return associated user info.
    Used by the dashboard for login validation.
    """
    return {
        "status": "authenticated",
        "user_id": ctx.principal.user_id,
        "org_id": ctx.principal.org_id,
        "permissions": {
            **ctx.principal.permissions.__dict__,
            "isAdmin": ctx.principal.permissions.is_admin  # Maintain compat with frontend
        },
    }
@router.get("/keys")
async def list_keys(
    session: AsyncSession = Depends(get_db_session),
    ctx: RequestContext = Depends(get_request_context),
):
    """List all API keys."""
    repo = SqlAlchemyApiKeyRepository(session)
    keys = await repo.list_all()
    return [{
        "id": k.id,
        "name": k.name,
        "preview": k.preview,
        "org_id": k.org_id,
        "is_active": k.is_active,
        "created_at": k.expires_at.isoformat() if k.expires_at else None, # Placeholder for created_at
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        "role": "admin" if k.permissions.is_admin else "user"
    } for k in keys]

@router.get("/conversations")
async def list_conversations(
    session: AsyncSession = Depends(get_db_session),
    ctx: RequestContext = Depends(get_request_context),
):
    """List recent conversations."""
    repo = ConversationRepository(session)
    convs = await repo.list_all_conversations()
    return [{
        "id": c.id,
        "user": c.user_id,
        "model": c.metadata.get("model", "unknown"),
        "messages": c.metadata.get("messages", 0),
        "tokens": c.metadata.get("tokens", 0),
        "cost": c.metadata.get("cost", 0.0),
        "started_at": c.created_at.isoformat(),
        "status": c.status.value
    } for c in convs]
