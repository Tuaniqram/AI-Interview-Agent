"""Shared Redis wiring for the state that worker processes must agree on.

Every feature built on this has to keep working when Redis is down, so the rules are:

* timeouts are short and there are no hidden client retries: a dead Redis must cost a turn
  milliseconds, not minutes;
* after a failure the feature skips Redis for ``RETRY_AFTER_S`` and uses its fallback, then tries
  again (a Redis that was down at startup is picked up as soon as it is back).
"""
import asyncio
import logging
import os
import time

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_S = float(os.getenv("REDIS_CONNECT_TIMEOUT_S", "2"))
SOCKET_TIMEOUT_S = float(os.getenv("REDIS_SOCKET_TIMEOUT_S", "3"))
RETRY_AFTER_S = float(os.getenv("REDIS_RETRY_AFTER_S", "5"))


def redis_url() -> str:
    return os.getenv("REDIS_URL", "").strip()


def _options() -> dict:
    return {
        "decode_responses": True,
        "socket_connect_timeout": CONNECT_TIMEOUT_S,
        "socket_timeout": SOCKET_TIMEOUT_S,
        "health_check_interval": 30,
    }


def create_sync_client():
    """A blocking client, or None without ``REDIS_URL``. Call it only from worker threads."""
    url = redis_url()
    if not url:
        return None
    try:
        from redis import Redis
        from redis.backoff import NoBackoff
        from redis.retry import Retry

        return Redis.from_url(url, retry=Retry(NoBackoff(), 0), **_options())
    except Exception as exc:  # noqa: BLE001 - a bad URL must not stop the app
        logger.warning("Redis client could not be created: %s", type(exc).__name__)
        return None


def create_async_client():
    """A ``redis.asyncio`` client, or None without ``REDIS_URL``."""
    url = redis_url()
    if not url:
        return None
    try:
        from redis.asyncio import Redis
        from redis.asyncio.retry import Retry
        from redis.backoff import NoBackoff

        return Redis.from_url(url, retry=Retry(NoBackoff(), 0), **_options())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis client could not be created: %s", type(exc).__name__)
        return None


class Breaker:
    """Remembers that Redis just failed, so callers use their fallback for a short while."""

    def __init__(self, feature: str, retry_after: float = RETRY_AFTER_S, clock=time.monotonic):
        self.feature = feature
        self.retry_after = retry_after
        self._clock = clock
        self._down_until = 0.0

    def allows(self) -> bool:
        return self._clock() >= self._down_until

    def failed(self, exc: Exception) -> None:
        self._down_until = self._clock() + self.retry_after
        logger.warning("Redis unavailable for %s, using the fallback: %s: %s",
                       self.feature, type(exc).__name__, str(exc)[:200])

    def reset(self) -> None:
        self._down_until = 0.0


class AsyncLink:
    """One feature's async Redis connection plus its breaker.

    A ``redis.asyncio`` client belongs to the event loop that created it, so it is made per loop.
    ``client`` is an injection point for tests.
    """

    def __init__(self, feature: str, client=None):
        self._injected = client
        self.last_client = client
        self._loop = None
        self.breaker = Breaker(feature)

    def client(self):
        """The client, or None when there is no Redis or it just failed."""
        if self._injected is None:
            loop = asyncio.get_running_loop()
            if self._loop is not loop:
                self._loop, self.last_client = loop, create_async_client()
        return self.last_client if self.breaker.allows() else None

    def failed(self, exc: Exception) -> None:
        self.breaker.failed(exc)
