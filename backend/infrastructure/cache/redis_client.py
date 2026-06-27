"""
CrimePatrol — Redis Client (caching + WebSocket pub/sub)
"""
from typing import Any

import redis.asyncio as aioredis

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    """Initialize Redis connection pool. Called at app startup."""
    global _redis
    settings = get_settings()
    _redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_keepalive=True,
    )
    await _redis.ping()
    logger.info("redis_connected", url=settings.redis_url)


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        logger.info("redis_closed")


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis


# =============================================================================
# Cache Helpers
# =============================================================================

async def cache_get(key: str) -> str | None:
    return await get_redis().get(key)


async def cache_set(key: str, value: str, ttl: int | None = None) -> None:
    settings = get_settings()
    await get_redis().set(key, value, ex=ttl or settings.redis_ttl_seconds)


async def cache_delete(key: str) -> None:
    await get_redis().delete(key)


async def cache_invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count deleted."""
    keys = await get_redis().keys(pattern)
    if keys:
        return await get_redis().delete(*keys)
    return 0


# =============================================================================
# Pub/Sub (WebSocket fan-out)
# =============================================================================

async def publish(channel: str, message: str) -> None:
    await get_redis().publish(channel, message)


def get_pubsub() -> aioredis.client.PubSub:
    return get_redis().pubsub()
