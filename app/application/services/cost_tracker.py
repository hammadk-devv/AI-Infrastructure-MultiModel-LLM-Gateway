import asyncio
import json
import time
from decimal import Decimal
from typing import Any, Dict, Optional

from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.budget import BudgetStatus

logger = get_logger(__name__)

class CostTrackerService:
    """
    Real-time cost tracking and budget enforcement.
    
    Uses Redis for low-latency counters and Postgres for persistence.
    """

    def __init__(self, redis: Redis, session_factory: Any):
        self._redis = redis
        self._session_factory = session_factory

    async def track_usage(
        self,
        org_id: str,
        user_id: str,
        model: str,
        provider: str,
        cost: Decimal,
        tokens: int,
    ):
        """Record usage and update real-time counters."""
        
        # 1. Update Redis counters (atomic)
        now = time.gmtime()
        daily_key = f"lkg:budget:org:{org_id}:daily:{now.tm_year}:{now.tm_yday}"
        monthly_key = f"lkg:budget:org:{org_id}:monthly:{now.tm_year}:{now.tm_mon}"
        
        async with self._redis.pipeline() as pipe:
            pipe.incrbyfloat(f"{daily_key}:cost", float(cost))
            pipe.incrby(f"{daily_key}:tokens", tokens)
            pipe.incrbyfloat(f"{monthly_key}:cost", float(cost))
            pipe.incrby(f"{monthly_key}:tokens", tokens)
            
            # Set TTLs (2 days for daily, 60 days for monthly)
            pipe.expire(f"{daily_key}:cost", 172800)
            pipe.expire(f"{monthly_key}:cost", 5184000)
            
            await pipe.execute()

        # 2. Check for alerts (asynchronous/non-blocking)
        # In a real system, we'd trigger a webhook or message queue here

    async def get_org_status(self, org_id: str) -> BudgetStatus:
        """Get current month budget status for an organization."""
        now = time.gmtime()
        monthly_key = f"lkg:budget:org:{org_id}:monthly:{now.tm_year}:{now.tm_mon}:cost"
        
        current_spend_raw = await self._redis.get(monthly_key)
        current_spend = Decimal(str(current_spend_raw.decode()) if current_spend_raw else "0.0")
        
        # In a real system, we'd fetch the limit from DB or cache
        limit = Decimal("1000.00") # Default $1000 limit
        
        return BudgetStatus(
            org_id=org_id,
            current_spend=current_spend,
            limit=limit,
            is_exceeded=current_spend >= limit,
            utilization_percent=float(current_spend / limit) * 100 if limit > 0 else 0
        )
