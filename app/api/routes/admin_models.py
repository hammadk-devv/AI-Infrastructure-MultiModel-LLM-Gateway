from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_db_session,
    get_model_registry,
    get_request_context,
)
from app.application.auth.context import RequestContext
from app.domain.models import ModelCapability
from app.domain.services.model_registry import ModelRegistry
from app.infrastructure.models import AuditLogModel, ModelConfigModel

router = APIRouter(prefix="/admin/models", tags=["admin"])


class ModelConfigCreate(BaseModel):
    provider: str = Field(..., example="openai")
    model_name: str = Field(..., example="gpt-4o")
    display_name: str = Field(..., example="GPT-4o")
    context_window: int = Field(..., example=128000)
    max_output_tokens: int = Field(..., example=4096)
    capabilities: list[ModelCapability] = Field(default_factory=list)
    cost_per_1k_input: float = Field(default=0.0)
    cost_per_1k_output: float = Field(default=0.0)
    priority: int = Field(default=0)
    is_active: bool = Field(default=True)


class ModelConfigUpdate(BaseModel):
    display_name: str | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    capabilities: list[ModelCapability] | None = None
    cost_per_1k_input: float | None = None
    cost_per_1k_output: float | None = None
    priority: int | None = None
    is_active: bool | None = None


def check_admin(ctx: RequestContext = Depends(get_request_context)) -> None:
    """Ensure the caller has administrative permissions."""
    if not ctx.principal.permissions.can_manage_keys:
        raise HTTPException(status_code=403, detail="Admin permissions required")


@router.get("")
async def list_models(
    db: AsyncSession = Depends(get_db_session),
    _ = Depends(check_admin),
) -> list[dict[str, Any]]:
    stmt = select(ModelConfigModel).order_by(ModelConfigModel.provider, ModelConfigModel.priority.desc())
    result = await db.execute(stmt)
    models = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "provider": m.provider,
            "model_name": m.model_name,
            "display_name": m.display_name,
            "is_active": m.is_active,
            "priority": m.priority,
        }
        for m in models
    ]


@router.post("")
async def create_model(
    config: ModelConfigCreate,
    db: AsyncSession = Depends(get_db_session),
    ctx: RequestContext = Depends(get_request_context),
    _ = Depends(check_admin),
) -> dict[str, Any]:
    model_id = str(uuid4())
    
    db_model = ModelConfigModel(
        id=model_id,
        provider=config.provider,
        model_name=config.model_name,
        display_name=config.display_name,
        context_window=config.context_window,
        max_output_tokens=config.max_output_tokens,
        capabilities=json.dumps([c.value for c in config.capabilities]),
        cost_per_1k_input=config.cost_per_1k_input,
        cost_per_1k_output=config.cost_per_1k_output,
        priority=config.priority,
        is_active=config.is_active,
    )
    db.add(db_model)

    # Audit log
    audit = AuditLogModel(
        id=str(uuid4()),
        user_id=ctx.principal.user_id,
        action="CREATE",
        entity_type="model_config",
        entity_id=model_id,
        new_values=config.model_dump(),
        ip_address=ctx.client_ip,
    )
    db.add(audit)
    
    await db.commit()
    return {"id": str(model_id), "status": "created"}


@router.patch("/{model_id}")
async def update_model(
    model_id: str,
    update: ModelConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
    ctx: RequestContext = Depends(get_request_context),
    _ = Depends(check_admin),
) -> dict[str, Any]:
    stmt = select(ModelConfigModel).where(ModelConfigModel.id == model_id)
    result = await db.execute(stmt)
    db_model = result.scalar_one_or_none()
    
    if not db_model:
        raise HTTPException(status_code=404, detail="Model config not found")

    old_values = {
        "display_name": db_model.display_name,
        "context_window": db_model.context_window,
        "max_output_tokens": db_model.max_output_tokens,
        "capabilities": db_model.capabilities,
        "cost_per_1k_input": float(db_model.cost_per_1k_input),
        "cost_per_1k_output": float(db_model.cost_per_1k_output),
        "priority": db_model.priority,
        "is_active": db_model.is_active,
    }

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "capabilities":
            setattr(db_model, key, [c.value for c in value])
        else:
            setattr(db_model, key, value)

    # Audit log
    audit = AuditLogModel(
        id=uuid4(),
        user_id=ctx.principal.user_id,
        action="UPDATE",
        entity_type="model_config",
        entity_id=str(model_id),
        old_values=old_values,
        new_values=update_data,
        ip_address=ctx.client_ip,
    )
    db.add(audit)
    
    await db.commit()
    return {"status": "updated"}


@router.delete("/{model_id}")
async def delete_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    ctx: RequestContext = Depends(get_request_context),
    _ = Depends(check_admin),
) -> dict[str, Any]:
    stmt = select(ModelConfigModel).where(ModelConfigModel.id == model_id)
    result = await db.execute(stmt)
    db_model = result.scalar_one_or_none()
    
    if not db_model:
        raise HTTPException(status_code=404, detail="Model config not found")

    # Soft delete? Or hard delete for config?
    # Registry only picks up is_active=True, but let's hard delete if explicitly requested.
    await db.delete(db_model)

    # Audit log
    audit = AuditLogModel(
        id=uuid4(),
        user_id=ctx.principal.user_id,
        action="DELETE",
        entity_type="model_config",
        entity_id=str(model_id),
        old_values={"model_name": db_model.model_name, "provider": db_model.provider},
        ip_address=ctx.client_ip,
    )
    db.add(audit)
    
    await db.commit()
    return {"status": "deleted"}


@router.post("/refresh")
async def refresh_registry(
    registry: ModelRegistry = Depends(get_model_registry),
    _ = Depends(check_admin),
) -> dict[str, str]:
    """Manually trigger a refresh of the model registry from DB."""
    await registry.refresh()
    return {"status": "refreshed"}
