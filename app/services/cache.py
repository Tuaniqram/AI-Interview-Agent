"""
Distributed cache service using Redis.
Provides async TTL-based caching with automatic fallback when Redis is unavailable.
"""
import json
import logging
import os
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")


class RedisCache:
    """
    Async Redis cache with TTL support.
    Falls back to no-op when Redis is unavailable.
    """

    def __init__(self):
        self._client = None
        self._enabled = False

    async def init(self):
        if not REDIS_URL:
            logger.info("REDIS_URL not set — Redis cache disabled")
            return
        try:
            from redis.asyncio import Redis
            self._client = Redis.from_url(REDIS_URL, decode_responses=True)
            await self._client.ping()
            self._enabled = True
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, cache disabled: {e}")
            self._client = None
            self._enabled = False

    async def get(self, key: str) -> Optional[str]:
        if not self._enabled or not self._client:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        if not self._enabled or not self._client:
            return
        try:
            await self._client.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    async def delete(self, key: str) -> None:
        if not self._enabled or not self._client:
            return
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled


# Singleton
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
