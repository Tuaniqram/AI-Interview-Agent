"""One interview step at a time across workers. Each ``DistributedSessionLocks`` stands for a worker."""
import asyncio
import json

import fakeredis
import pytest
from fakeredis import FakeAsyncRedis
from starlette.testclient import TestClient

from app.api import interview_ws
from app.auth.interview_access import create_interview_access_token
from app.engine.engine import InterviewEngine
from app.engine.session_lock import LOCK_KEY_PREFIX, DistributedSessionLocks, SessionBusy
from app.services.v4_session_store import RedisV4SessionStore
from tests.conftest import (
    CONDUCTOR_TURN_JSON,
    EVALUATOR_JSON,
    GOVERNOR_JSON,
    STRATEGY_JSON,
    StubLLM,
    make_v4_state,
)

SID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture
def server():
    return fakeredis.FakeServer()


def worker_locks(server, ttl_s=330):
    return DistributedSessionLocks(ttl_s=ttl_s, client=FakeAsyncRedis(server=server, decode_responses=True))


async def test_only_one_of_two_workers_runs_the_turn(server, monkeypatch, fake_evidence_repo, fake_repos):
    class SlowLLM(StubLLM):
        async def invoke(self, prompt, **kwargs):
            await asyncio.sleep(0.02)  # the turn is in progress while the second request arrives
            return await super().invoke(prompt, **kwargs)

    turn = [json.dumps(EVALUATOR_JSON), GOVERNOR_JSON, CONDUCTOR_TURN_JSON]
    llm = SlowLLM(responses=[STRATEGY_JSON, "Question: First question?", *turn, *turn])
    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: llm)

    def store():  # no durable tier: the shared state is the fake Redis
        return RedisV4SessionStore(redis_client=fakeredis.FakeStrictRedis(server=server, decode_responses=True))

    store_a, store_b = store(), store()
    await InterviewEngine(store=store_a).start_session(make_v4_state(session_id="s1"))
    before = store_a.get("s1")["question_number"]

    async def answer(locks, shared_store):
        async with locks.lock("s1"):
            return await InterviewEngine(store=shared_store).process_answer("s1", "I added idempotency keys.")

    results = await asyncio.gather(
        answer(worker_locks(server), store_a), answer(worker_locks(server), store_b), return_exceptions=True
    )

    assert sum(isinstance(r, SessionBusy) for r in results) == 1, results
    assert sum(isinstance(r, dict) for r in results) == 1, results
    state = store_b.get("s1")
    assert state["question_number"] == before + 1
    assert [e["role"] for e in state["conversation_history"]].count("user") == 1


async def test_lock_is_released_for_the_next_turn_and_has_a_ttl(server):
    a, b = worker_locks(server), worker_locks(server)
    redis = FakeAsyncRedis(server=server, decode_responses=True)
    async with a.lock("s"):
        assert 300_000 < await redis.pttl(LOCK_KEY_PREFIX + "s") <= 330_000
    async with b.lock("s"):
        pass
    assert await redis.exists(LOCK_KEY_PREFIX + "s") == 0


async def test_release_leaves_a_lock_somebody_else_now_holds(server):
    redis = FakeAsyncRedis(server=server, decode_responses=True)
    async with worker_locks(server).lock("s"):
        await redis.set(LOCK_KEY_PREFIX + "s", "another-token")  # ours expired and was retaken
    assert await redis.get(LOCK_KEY_PREFIX + "s") == "another-token"


async def test_released_when_the_turn_fails(server):
    a = worker_locks(server)
    with pytest.raises(RuntimeError):
        async with a.lock("s"):
            raise RuntimeError("turn failed")
    async with worker_locks(server).lock("s"):
        pass


async def test_waiting_step_runs_after_the_running_one(server):
    a, b = worker_locks(server), worker_locks(server)
    order = []

    async def step(locks, name, wait):
        async with locks.lock("s", wait=wait):
            order.append(f"{name} in")
            await asyncio.sleep(0.05)
            order.append(f"{name} out")

    first = asyncio.create_task(step(a, "first", 0))
    await asyncio.sleep(0.01)
    await asyncio.gather(first, step(b, "second", 5))
    assert order == ["first in", "first out", "second in", "second out"]


async def test_redis_down_falls_back_to_the_process_lock(server):
    server.connected = False
    locks = worker_locks(server)
    async with locks.lock("s"):
        with pytest.raises(SessionBusy):
            async with locks.lock("s"):
                pass
    async with locks.lock("s"):
        pass


def test_websocket_replies_busy_while_another_worker_holds_the_session(server, monkeypatch):
    from app.main import app

    answers = []

    class FakeEngine:
        def __init__(self, *a, **k):
            pass

        async def process_answer(self, sid, answer, integrity_meta=None):
            answers.append(answer)
            return {"status": "in_progress"}

    monkeypatch.setattr(interview_ws, "InterviewEngine", FakeEngine)
    monkeypatch.setattr(interview_ws, "_session_locks", worker_locks(server))
    fakeredis.FakeStrictRedis(server=server).set(LOCK_KEY_PREFIX + SID, "held-by-worker-2")

    url = f"/ws/interview/{SID}?access={create_interview_access_token(SID)}"
    with TestClient(app).websocket_connect(url) as ws:
        ws.receive_json()
        ws.send_text(json.dumps({"type": "submit_answer", "candidate_answer": "hello", "_id": "7"}))
        assert ws.receive_json()["phase"] == "evaluating"
        reply = ws.receive_json()
    assert reply == {"type": "error", "code": "busy", "detail": interview_ws.BUSY_DETAIL, "_id": "7"}
    assert answers == []
