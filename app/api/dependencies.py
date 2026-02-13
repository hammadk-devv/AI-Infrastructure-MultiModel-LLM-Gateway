from __future__ import annotations

from fastapi import HTTPException, Request

from app.application.auth.context import RequestContext
from app.application.llm.factory import ProviderAdapterFactory
from app.application.services.model_router import ModelRouterService
from app.domain.services.model_registry import ModelRegistry
from app.infrastructure.db import get_db_session


def get_request_context(request: Request) -> RequestContext:
    """Return the RequestContext injected by the authentication middleware."""

    context = getattr(request.state, "request_context", None)
    if context is None:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    return context


def get_model_registry(request: Request) -> ModelRegistry:
    """Return the ModelRegistry singleton."""
    return request.app.state.model_registry


def get_provider_factory(request: Request) -> ProviderAdapterFactory:
    """Return the ProviderAdapterFactory singleton."""
    return request.app.state.provider_factory


def get_model_router(request: Request) -> ModelRouterService:
    """Return the ModelRouterService singleton."""
    return request.app.state.model_router

