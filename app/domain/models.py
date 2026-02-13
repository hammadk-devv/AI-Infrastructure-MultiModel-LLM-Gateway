from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class ModelCapability(str, Enum):
    STREAMING = "streaming"
    TOOLS = "tools"
    VISION = "vision"
    JSON_MODE = "json_mode"
    LONG_CONTEXT = "long_context"


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Domain entity for LLM model configuration."""

    id: str
    provider: str
    model_name: str
    display_name: str
    context_window: int
    max_output_tokens: int
    capabilities: list[ModelCapability] = field(default_factory=list)
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    is_active: bool = True
    priority: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuditLog:
    """Domain entity for audit logs."""

    id: str
    user_id: str | None
    action: str
    entity_type: str
    entity_id: str
    old_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: datetime | None = None
