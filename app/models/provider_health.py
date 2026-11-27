"""Which LLM providers are failing right now, shared by every chain and every worker process.

A breaker has three states:

* **open** - a recent failure; the model is only tried when nothing healthy is left;
* **half-open** - the cool-down ended but nobody has succeeded yet: one caller at a time probes it;
* **closed** - no record.

Account-wide failures block the whole provider, not just the model that happened to see them: an
OpenRouter 402/429 blocks its paid models, a 401 blocks the provider. Everything is kept in this
process as well, so the breaker still works (per worker) when Redis is down.

Redis keys (all with a TTL): ``aura:llm:cb:{scope}`` = wall-clock time the breaker stays open until,
``aura:llm:probe:{scope}``, ``aura:llm:errors:{provider}:{status}`` (last hour),
``aura:llm:tokens:{provider}:{model}:{day}`` (Groq's free tier has a daily token limit per model).
"""
import logging
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

PERMANENT_STATUS = frozenset({401, 402, 403, 404, 410})
PERMANENT_COOLDOWN_S = 15 * 60
TRANSIENT_COOLDOWN_S = 30
HALF_OPEN_WINDOW_S = 10 * 60   # how long after the cool-down a success is still required
PROBE_TTL_S = 30
ERROR_COUNT_TTL_S = 3600
TOKEN_TTL_S = 48 * 3600
PREFIX = "aura:llm:"

# Opens a breaker without ever shortening a longer one (a 30 s 429 must not cut a 15 min 402 short).
_OPEN_LUA = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
if current < tonumber(ARGV[1]) then redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2]) end
redis.call('DEL', KEYS[2])
redis.call('INCR', KEYS[3])
redis.call('EXPIRE', KEYS[3], ARGV[3])
return 1
"""


def groq_daily_token_limit() -> int:
    try:
        return max(0, int(os.getenv("GROQ_DAILY_TOKEN_LIMIT", "200000")))
    except ValueError:
        return 200_000


def provider_of(model) -> str:
    base = str(getattr(model, "openai_api_base", "") or "")
    host = urlparse(base).hostname or "other"
    if host.endswith("openrouter.ai"):
        return "openrouter"
    if host.endswith("groq.com"):
        return "groq"
    return "local" if host in ("localhost", "127.0.0.1") else host


def _is_paid(provider: str, name: str) -> bool:
    return provider == "openrouter" and name != "openrouter/free" and not name.endswith(":free")


def scopes_of(model) -> list[str]:
    provider, name = provider_of(model), model.model_name
    scopes = [f"model:{provider}:{name}", f"provider:{provider}"]
    if _is_paid(provider, name):
        scopes.append(f"paid:{provider}")
    return scopes


def failure_scope(model, status: int | None) -> str:
    provider, name = provider_of(model), model.model_name
    if status == 401 and provider != "other":
        return f"provider:{provider}"
    if status in (402, 429) and _is_paid(provider, name):
        return f"paid:{provider}"
    return f"model:{provider}:{name}"


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


class ProviderHealth:
    """``link`` is an ``AsyncLink``; without one the state is local to this object."""

    def __init__(self, link=None, clock=time.monotonic, now=time.time):
        self._link = link
        self._clock = clock
        self._now = now
        self._open_until: dict[str, float] = {}  # scope -> self._clock() value

    def _redis(self):
        return self._link.client() if self._link is not None else None

    async def inspect(self, models: list) -> tuple[list[float], list[bool]]:
        """Per model: seconds it stays blocked (0 = may be tried) and whether it needs a probe."""
        local_now = self._clock()
        blocked = [
            max([0.0] + [self._open_until.get(s, 0.0) - local_now for s in scopes_of(m)]) for m in models
        ]
        half_open = [False] * len(models)
        client = self._redis()
        if client is None:
            return blocked, half_open
        scopes = sorted({s for m in models for s in scopes_of(m)})
        groq = sorted({m.model_name for m in models if provider_of(m) == "groq"})
        keys = [f"{PREFIX}cb:{s}" for s in scopes] + [f"{PREFIX}tokens:groq:{n}:{_day()}" for n in groq]
        try:
            values = await client.mget(keys)
        except Exception as exc:  # noqa: BLE001
            self._link.failed(exc)
            return blocked, half_open
        until = dict(zip(scopes, values[: len(scopes)]))
        used = {n: int(v or 0) for n, v in zip(groq, values[len(scopes):])}
        now, limit = self._now(), groq_daily_token_limit()
        for i, model in enumerate(models):
            for scope in scopes_of(model):
                if until.get(scope) is None:
                    continue
                remaining = float(until[scope]) - now
                if remaining > 0:
                    blocked[i] = max(blocked[i], remaining)
                else:
                    half_open[i] = True
            if limit and provider_of(model) == "groq" and used.get(model.model_name, 0) >= limit:
                blocked[i] = max(blocked[i], float(TOKEN_TTL_S))
        return blocked, half_open

    async def claim_probe(self, model) -> bool:
        """True if this caller is the one that may test a half-open model."""
        client = self._redis()
        if client is None:
            return True
        try:
            key = f"{PREFIX}probe:{failure_scope(model, 402)}"
            return bool(await client.set(key, "1", nx=True, ex=PROBE_TTL_S))
        except Exception as exc:  # noqa: BLE001
            self._link.failed(exc)
            return True

    async def failed(self, model, status: int | None) -> None:
        cooldown = PERMANENT_COOLDOWN_S if status in PERMANENT_STATUS else TRANSIENT_COOLDOWN_S
        scope = failure_scope(model, status)
        self._open_until[scope] = max(self._open_until.get(scope, 0.0), self._clock() + cooldown)
        client = self._redis()
        if client is None:
            return
        try:
            await client.eval(
                _OPEN_LUA, 3, f"{PREFIX}cb:{scope}", f"{PREFIX}probe:{failure_scope(model, 402)}",
                f"{PREFIX}errors:{provider_of(model)}:{status or 'other'}",
                self._now() + cooldown, cooldown + HALF_OPEN_WINDOW_S, ERROR_COUNT_TTL_S,
            )
        except Exception as exc:  # noqa: BLE001
            self._link.failed(exc)

    async def succeeded(self, model, tokens: int = 0, was_suspect: bool = False) -> None:
        """``was_suspect``: this was a probe or a last-resort try, so the success closes its breakers.

        An ordinary success closes nothing: it may belong to a request sent before another worker
        saw the account run out.
        """
        scopes = scopes_of(model)
        if was_suspect:
            for scope in scopes:
                self._open_until.pop(scope, None)
        client = self._redis()
        if client is None:
            return
        try:
            if was_suspect:
                await client.delete(*[f"{PREFIX}cb:{s}" for s in scopes],
                                    f"{PREFIX}probe:{failure_scope(model, 402)}")
            if tokens and provider_of(model) == "groq":
                key = f"{PREFIX}tokens:groq:{model.model_name}:{_day()}"
                async with client.pipeline(transaction=False) as pipe:
                    pipe.incrby(key, tokens)
                    pipe.expire(key, TOKEN_TTL_S)
                    await pipe.execute()
        except Exception as exc:  # noqa: BLE001
            self._link.failed(exc)
