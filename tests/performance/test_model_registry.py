from __future__ import annotations

import asyncio
import time
import statistics
import logging
from uuid import uuid4

from app.application.services.model_registry_service import RedisModelRegistry
from app.infrastructure.redis_client import get_redis_client
from app.infrastructure.db import SessionLocal
from app.domain.models import ModelCapability

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def benchmark_registry(iterations: int = 1000):
    logger.info(f"Starting ModelRegistry benchmark with {iterations} iterations...")
    
    redis = get_redis_client()
    registry = RedisModelRegistry(
        redis=redis,
        session_factory=SessionLocal,
    )
    
    # Ensure warmed
    await registry.refresh()
    
    latencies = []
    
    # Get a model that we know exists from seed data
    model_id = "gpt-4o"
    
    for _ in range(iterations):
        start = time.perf_counter()
        model = await registry.get_model(model_id)
        end = time.perf_counter()
        
        if not model:
            logger.error("Model not found in registry during benchmark!")
            break
            
        latencies.append((end - start) * 1000) # ms

    if not latencies:
        return

    avg = statistics.mean(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    p99 = statistics.quantiles(latencies, n=100)[98] # 99th percentile
    
    logger.info("--- Benchmark Results ---")
    logger.info(f"Average Latency: {avg:.3f} ms")
    logger.info(f"P95 Latency:     {p95:.3f} ms")
    logger.info(f"P99 Latency:     {p99:.3f} ms")
    logger.info(f"Throughput:      {iterations / sum(latencies) * 1000:.1f} req/s")
    
    target_p95 = 5.0
    if p95 <= target_p95:
        logger.info(f"SUCCESS: P95 latency ({p95:.3f}ms) is within target ({target_p95}ms)")
    else:
        logger.warning(f"FAILURE: P95 latency ({p95:.3f}ms) exceeds target ({target_p95}ms)")

    await redis.aclose()

if __name__ == "__main__":
    asyncio.run(benchmark_registry())
