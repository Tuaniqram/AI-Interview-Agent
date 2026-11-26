"""One interview step at a time, across all worker processes.

``SessionLocks`` (asyncio) only stops two steps inside one process. ``DistributedSessionLocks`` adds a
Redis lock (``SET key token NX PX``, released only by the holder of the token), so the same answer
cannot be scored on two workers at once. Without Redis it falls back to the in-process lock.
"""
import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from app.engine.guards import SessionLocks
from app.services.redis_client import Breaker, create_async_client

logger = logging.getLogger(__name__)

LOCK_KEY_PREFIX = "aura:lock:"
POLL_S = 0.25

_RELEASE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
"""


class SessionBusy(Exception):
    """Another step of this interview is still running (here or on another worker)."""


class DistributedSessionLocks:
    """``async with locks.lock(session_id):`` raises ``SessionBusy`` instead of queueing.

    ``wait`` (seconds) lets an idempotent step, such as starting or resuming, wait for the running one.
    The TTL only matters if a worker dies while holding the lock; it must outlast the longest step, or a
    slow turn would lose its lock while still running.
    """

    def __init__(self, ttl_s: float, client=None):
        self.ttl_ms = int(ttl_s * 1000)
        self._local = SessionLocks()
        self._injected = client
        self._client = client
        self._loop = None
        self._breaker = Breaker("session locks")

    def _redis(self):
        if self._injected is None:  # a redis.asyncio client belongs to the event loop that created it
            loop = asyncio.get_running_loop()
            if self._loop is not loop:
                self._loop, self._client = loop, create_async_client()
        return self._client if self._client is not None and self._breaker.allows() else None

    @asynccontextmanager
    async def lock(self, session_id: str, wait: float = 0.0):
        deadline = time.monotonic() + wait
        while self._local.locked(session_id):
            if time.monotonic() >= deadline:
                raise SessionBusy(session_id)
            await asyncio.sleep(POLL_S)
        async with self._local.lock(session_id):  # free: taken without suspending
            key, token = LOCK_KEY_PREFIX + session_id, uuid.uuid4().hex
            held = await self._acquire(key, token, deadline)
            try:
                yield
            finally:
                if held:
                    await self._release(key, token)

    async def _acquire(self, key: str, token: str, deadline: float) -> bool:
        """True = we hold the Redis lock; False = Redis unavailable, the local lock alone applies."""
        while True:
            client = self._redis()
            if client is None:
                return False
            try:
                if await client.set(key, token, nx=True, px=self.ttl_ms):
                    return True
            except Exception as exc:  # noqa: BLE001
                self._breaker.failed(exc)
                return False
            if time.monotonic() >= deadline:
                raise SessionBusy(key.removeprefix(LOCK_KEY_PREFIX))
            await asyncio.sleep(POLL_S)

    async def _release(self, key: str, token: str) -> None:
        # Try even if the breaker is open: a lock left behind blocks the candidate until its TTL.
        try:
            await self._client.eval(_RELEASE_LUA, 1, key, token)
        except Exception as exc:  # noqa: BLE001
            self._breaker.failed(exc)
