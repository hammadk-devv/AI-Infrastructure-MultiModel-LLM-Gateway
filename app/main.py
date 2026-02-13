from __future__ import annotations

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request

from fastapi.middleware.cors import CORSMiddleware
from app.api.middleware.auth import ApiKeyAuthMiddleware
from app.api.middleware.compliance import ComplianceMiddleware
from app.api.routes import admin_models, chat, conversations, health, metrics, dashboard
from app.application.llm.factory import ProviderAdapterFactory
from app.application.services.memory_registry_service import InMemoryModelRegistry
from app.application.services.model_registry_service import RedisModelRegistry
from app.application.services.model_router import ModelRouterService
from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings
from app.domain.services.model_registry import ModelRegistry
from app.infrastructure.db import SessionLocal, engine
from app.infrastructure.memory_client import get_memory_redis
from app.infrastructure.redis_client import get_redis_client
from app.application.llm.anthropic_adapter import AnthropicAdapter
from app.application.llm.gemini_adapter import GeminiAdapter
from app.application.llm.openai_adapter import OpenAIAdapter


settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context."""

    configure_logging(json=settings.environment != "dev")

    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

    # Initialize shared services
    if settings.redis_url == "memory://":
        redis = get_memory_redis()
        registry = InMemoryModelRegistry(session_factory=SessionLocal)
    else:
        redis = get_redis_client()
        registry = RedisModelRegistry(
            redis=redis,
            session_factory=SessionLocal,
        )

    factory = ProviderAdapterFactory()
    router_service = ModelRouterService(
        redis=redis,
        registry=registry,
        factory=factory
    )

    # Start background tasks
    await registry.start()

    # Store in app state for dependencies
    app.state.model_registry = registry
    app.state.provider_factory = factory
    app.state.model_router = router_service

    # Optionally test DB connection on startup.
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)

    yield

    # Cleanup
    await registry.stop()
    await factory.shutdown()
    await redis.aclose()
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"Incoming {request.method} request to {request.url.path}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(ApiKeyAuthMiddleware)
    app.add_middleware(ComplianceMiddleware, allowed_regions=settings.allowed_regions if hasattr(settings, "allowed_regions") else None)

    @app.get("/")
    async def root():
        return {
            "name": settings.app_name,
            "version": settings.api_version,
            "status": "online",
            "message": "Welcome to the AI Gateway. Access /internal/health for status."
        }

    app.include_router(health.router, prefix="/internal")
    app.include_router(metrics.router, prefix="/internal")
    app.include_router(dashboard.router)
    app.include_router(conversations.router, prefix="/v1")
    app.include_router(chat.router)
    app.include_router(admin_models.router)

    return app


app = create_app()

