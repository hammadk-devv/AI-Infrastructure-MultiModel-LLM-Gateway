import asyncio
import logging
from app.infrastructure.redis_client import get_redis_client
from app.infrastructure.db import SessionLocal
from app.application.services.model_registry_service import RedisModelRegistry
from app.core.logging import configure_logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def warm_cache():
    logger.info("Initializing services for cache warming...")
    redis = get_redis_client()
    try:
        registry = RedisModelRegistry(
            redis=redis,
            session_factory=SessionLocal,
        )
        
        logger.info("Starting registry refresh...")
        await registry.refresh()
        logger.info("Successfully warmed model registry cache.")
    except Exception as e:
        logger.error(f"Failed to warm cache: {e}")
        exit(1)
    finally:
        await redis.aclose()

if __name__ == "__main__":
    asyncio.run(warm_cache())
