import asyncio
import redis.asyncio as aioredis
from .config import settings

_redis: aioredis.Redis | None = None
_lock: asyncio.Lock | None = None


def get_redis() -> aioredis.Redis:
    """Get or lazily create a thread-safe Redis connection (singleton)."""
    global _redis, _lock
    if _redis is not None:
        return _redis
    # Fallback for sync-first calls: create without lock
    _redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    return _redis


async def _get_redis_async() -> aioredis.Redis:
    """Async-safe lazy init with lock. Call from startup if needed."""
    global _redis, _lock
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        if _redis is None:
            _redis = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
