from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

class BudgetConfig(BaseModel):
    """Organization budget limits."""
    org_id: str
    monthly_limit: Decimal
    soft_limit_percent: float = 0.8
    hard_limit_percent: float = 1.0
    is_active: bool = True

class UsageQuotas(BaseModel):
    """User-level quotas."""
    user_id: str
    daily_token_limit: int
    monthly_token_limit: int

class BudgetStatus(BaseModel):
    """Current budget consumption status."""
    org_id: str
    current_spend: Decimal
    limit: Decimal
    is_exceeded: bool
    utilization_percent: float
