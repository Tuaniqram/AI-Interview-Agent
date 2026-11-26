"""The Redis features against a real server (fakeredis cannot prove the Lua scripts or the timeouts).

Opt-in:  TEST_REDIS_URL=rediss://... venv/Scripts/python.exe -m pytest tests/integration/test_redis_real.py -m integration
It only touches keys with a random ``it-`` id, and removes them.
"""
import os
import uuid

import pytest

from app.exceptions import StaleSessionError
from app.services.v4_session_store import REDIS_KEY_PREFIX, RedisV4SessionStore

pytestmark = pytest.mark.integration


@pytest.fixture
def url(monkeypatch):
    value = os.environ.get("TEST_REDIS_URL", "")
    if not value:
        pytest.skip("TEST_REDIS_URL not set")
    monkeypatch.setenv("REDIS_URL", value)
    return value


@pytest.fixture
def sid(url):
    session_id = f"it-{uuid.uuid4()}"
    yield session_id
    RedisV4SessionStore()._client.delete(f"{REDIS_KEY_PREFIX}{session_id}")


def test_two_workers_share_one_session(sid):
    a, b = RedisV4SessionStore(), RedisV4SessionStore()
    a.set(sid, {"session_id": sid, "question_number": 1})
    old = a.get(sid)
    newer = b.get(sid)
    newer["question_number"] = 2
    b.set(sid, newer)

    assert a.get(sid)["question_number"] == 2
    old["question_number"] = 99
    with pytest.raises(StaleSessionError):
        a.set(sid, old)
    assert b.get(sid)["question_number"] == 2
    assert 0 < a._client.ttl(f"{REDIS_KEY_PREFIX}{sid}") <= 24 * 3600


async def test_lock_across_workers(url):
    from app.engine.session_lock import DistributedSessionLocks, SessionBusy

    sid = f"it-{uuid.uuid4()}"
    a, b = DistributedSessionLocks(ttl_s=30), DistributedSessionLocks(ttl_s=30)
    async with a.lock(sid):
        with pytest.raises(SessionBusy):
            async with b.lock(sid):
                pass
    async with b.lock(sid):
        pass


async def test_rate_limit_and_budget_scripts(url, monkeypatch):
    from app.middleware.rate_limit import RateLimitMiddleware
    from app.services import llm_budget
    from app.services.redis_client import create_async_client

    unique = uuid.uuid4().hex
    a = RateLimitMiddleware(None, max_requests=3, window_seconds=30, name=f"it-{unique}")
    b = RateLimitMiddleware(None, max_requests=3, window_seconds=30, name=f"it-{unique}")
    assert [await (a, b)[i % 2]._allow_shared("ip") for i in range(5)] == [True, True, True, False, False]

    monkeypatch.setenv("LLM_BUDGET_SESSION_CALLS", "2")
    budget = llm_budget.Budget()
    assert [await budget.take(f"it-{unique}", None) for _ in range(3)] == [0, 0, 1]

    redis = create_async_client()
    await redis.delete(f"{llm_budget.KEY_PREFIX}session:it-{unique}",
                       *[k async for k in redis.scan_iter(f"aura:rl:it-{unique}:*", count=1000)])
    await redis.aclose()


async def test_provider_breaker_across_workers(url):
    from types import SimpleNamespace

    from app.models.provider_health import PREFIX, ProviderHealth
    from app.services.redis_client import AsyncLink

    name = f"it-{uuid.uuid4().hex}"  # an unknown host: its own provider, no real model is blocked
    model = SimpleNamespace(model_name=name, openai_api_base=f"https://{name}.invalid/v1")
    a = ProviderHealth(link=AsyncLink("it"))
    b = ProviderHealth(link=AsyncLink("it"))
    await a.failed(model, 404)
    blocked, _ = await b.inspect([model])
    assert 800 < blocked[0] <= 900
    await b.succeeded(model, was_suspect=True)
    assert (await b.inspect([model]))[0] == [0]
    redis = a._link.client()
    await redis.delete(*[k async for k in redis.scan_iter(f"{PREFIX}errors:{name}*", count=1000)] or [f"{PREFIX}none"])


async def test_report_queue_and_events(url, monkeypatch):
    import asyncio

    from app.engine import report_jobs

    unique = f"it-{uuid.uuid4()}"
    monkeypatch.setattr(report_jobs, "STREAM", f"aura:events:{unique}:jobs")  # never the live queue
    done = []

    async def build(sid):
        done.append(sid)

    class Store:
        def get(self, sid):
            return {"finalized": bool(done)}

    producer, consumer = report_jobs.ReportQueue(builder=build), report_jobs.ReportQueue(builder=build)
    waiting = asyncio.create_task(producer.wait_for_report(unique, Store(), timeout=30, check_every=25))
    await asyncio.sleep(1)
    assert await producer.enqueue(unique) is True
    assert await consumer.run_once() is True  # creates the group
    assert await consumer.run_once() is True
    assert done == [unique]
    assert (await asyncio.wait_for(waiting, timeout=10))["finalized"]  # woken by the event
    redis = consumer._redis.client()
    assert await redis.ttl(report_jobs.STREAM) > 0
    await redis.delete(report_jobs.STREAM, report_jobs.QUEUED_PREFIX + unique)
