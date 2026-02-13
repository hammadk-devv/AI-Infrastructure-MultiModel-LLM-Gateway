from typing import Any
from fastapi import APIRouter, Request
from sqlalchemy import text


router = APIRouter(tags=["health"])


@router.get("/health", summary="Readiness probe")
async def health(request: Request) -> dict[str, Any]:
    """Check health of backend and dependencies."""
    
    health_status: dict[str, Any] = {
        "status": "healthy",
        "dependencies": {
            "database": "unknown",
            "redis": "unknown"
        }
    }

    # Check Database
    try:
        from app.infrastructure.db import SessionLocal
        from sqlalchemy import text
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        health_status["dependencies"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        from app.core.settings import get_settings
        settings = get_settings()
        
        if settings.redis_url == "memory://":
            health_status["dependencies"]["redis"] = "healthy (in-memory)"
        else:
            # Accessing registry from state
            registry = request.app.state.model_registry
            # Redis is stored as _redis in RedisModelRegistry
            if hasattr(registry, "_redis"):
                await registry._redis.ping()
                health_status["dependencies"]["redis"] = "healthy"
            else:
                health_status["dependencies"]["redis"] = "unhealthy: redis client missing in registry"
                health_status["status"] = "degraded"
    except Exception as e:
        health_status["dependencies"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    return health_status

