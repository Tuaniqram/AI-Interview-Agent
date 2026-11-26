"""A cap on LLM calls per interview and per organization per day, counted in Redis for all workers.

It stops a runaway interview (a loop, an abusive client, a bug) from spending the balance. The engine
opens a ``scope`` around its work; ``LLMService`` asks ``consume()`` before every call. Calls made
outside a scope (CV upload, fit evaluation) are not counted. Without Redis each worker counts for
itself.

Defaults, from 58 simulated 14-question interviews (30-47 calls on answer turns, median 36, plus the
calls that prepare the interview): 150 per interview is about three times a normal one and still above
a worst case with clarifications and the anti-cheat judge; 5000 per organization per day is about 100
interviews. ``0`` turns a cap off.
"""
import logging
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

from app.services.redis_client import AsyncLink

logger = logging.getLogger(__name__)

KEY_PREFIX = "aura:llm:budget:"
SESSION_TTL_S = 24 * 3600
ORG_TTL_S = 48 * 3600

# KEYS = session counter [, organization counter]; ARGV = session cap, session TTL, org cap, org TTL.
# Returns 0 = allowed (and counted), 1 = session cap reached, 2 = organization cap reached.
_CONSUME_LUA = """
for i, key in ipairs(KEYS) do
  local cap = tonumber(ARGV[i * 2 - 1])
  if cap > 0 and tonumber(redis.call('GET', key) or '0') >= cap then return i end
end
for i, key in ipairs(KEYS) do
  if redis.call('INCR', key) == 1 then redis.call('EXPIRE', key, ARGV[i * 2]) end
end
return 0
"""


def _cap(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def session_cap() -> int:
    return _cap("LLM_BUDGET_SESSION_CALLS", 150)


def org_daily_cap() -> int:
    return _cap("LLM_BUDGET_ORG_DAILY_CALLS", 5000)


class Scope:
    def __init__(self, session_id: str, org_id=None):
        self.session_id = str(session_id)
        self.org_id = str(org_id) if org_id else None
        self.exceeded = False


_current: ContextVar["Scope | None"] = ContextVar("llm_budget_scope", default=None)


@contextmanager
def scope(session_id: str, org_id=None):
    """LLM calls made inside count against this interview. Re-entering the same one keeps its flag."""
    active = _current.get()
    if active is not None and active.session_id == str(session_id):
        yield active
        return
    token = _current.set(Scope(session_id, org_id))
    try:
        yield _current.get()
    finally:
        _current.reset(token)


def exceeded() -> bool:
    active = _current.get()
    return bool(active and active.exceeded)


class Budget:
    def __init__(self, client=None):
        self._redis = AsyncLink("LLM budget", client)
        self._local: dict[str, tuple[int, float]] = {}  # key -> (count, expires at)

    async def take(self, session_id: str, org_id: str | None) -> int:
        """0 = allowed and counted, 1 = interview cap reached, 2 = organization cap reached."""
        counters = [(f"{KEY_PREFIX}session:{session_id}", session_cap(), SESSION_TTL_S)]
        if org_id:
            day = datetime.now(timezone.utc).strftime("%Y%m%d")
            counters.append((f"{KEY_PREFIX}org:{org_id}:{day}", org_daily_cap(), ORG_TTL_S))
        client = self._redis.client()
        if client is not None:
            try:
                args = [value for _, cap, ttl in counters for value in (cap, ttl)]
                return int(await client.eval(_CONSUME_LUA, len(counters), *[c[0] for c in counters], *args))
            except Exception as exc:  # noqa: BLE001 - never fail a turn because Redis is down
                self._redis.failed(exc)
        return self._take_local(counters)

    def _take_local(self, counters) -> int:
        now = time.monotonic()
        if len(self._local) > 10_000:
            self._local = {k: v for k, v in self._local.items() if v[1] > now}
        counts = {}
        for index, (key, cap, _ttl) in enumerate(counters, 1):
            count, expires = self._local.get(key, (0, 0.0))
            counts[key] = count if expires > now else 0
            if cap and counts[key] >= cap:
                return index
        for key, _cap_, ttl in counters:
            expires = self._local[key][1] if counts[key] else now + ttl
            self._local[key] = (counts[key] + 1, expires)
        return 0


_budget = Budget()


async def consume() -> bool:
    """May the current interview make one more LLM call? Always True outside a scope."""
    active = _current.get()
    if active is None:
        return True
    verdict = await _budget.take(active.session_id, active.org_id)
    if verdict == 0:
        return True
    if not active.exceeded:
        logger.warning("LLM budget used up for %s (session %s)",
                       "the organization today" if verdict == 2 else "this interview", active.session_id[:12])
    active.exceeded = True
    return False
