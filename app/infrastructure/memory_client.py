from __future__ import annotations

import asyncio
from typing import Any, Optional


class InMemoryRedis:
    """A minimal in-memory mock of a Redis client for local use."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            return self._data.get(key)

    async def set(
        self, 
        key: str, 
        value: str, 
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
    ) -> bool:
        async with self._lock:
            if nx and key in self._data:
                return False
            self._data[key] = value
            # Expiration not implemented for this simple version
            return True

    async def incr(self, key: str) -> int:
        async with self._lock:
            val = self._data.get(key, 0)
            if isinstance(val, bytes):
                try:
                    val = int(val.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    val = 0
            elif not isinstance(val, int):
                val = 0
            
            new_val = val + 1
            self._data[key] = new_val
            return new_val

    async def expire(self, key: str, seconds: int) -> bool:
        # Simple mock: we don't actually expire yet
        return True

    async def ttl(self, key: str) -> int:
        # Simple mock: return a reasonable TTL
        return 60

    async def delete(self, *keys: str) -> int:
        count = 0
        async with self._lock:
            for k in keys:
                if k in self._data:
                    del self._data[k]
                    count += 1
        return count

    async def exists(self, key: str) -> bool:
        async with self._lock:
            return key in self._data

    async def aclose(self) -> None:
        pass

_memory_redis = InMemoryRedis()

def get_memory_redis() -> InMemoryRedis:
    """Return the global in-memory Redis instance."""
    return _memory_redis
