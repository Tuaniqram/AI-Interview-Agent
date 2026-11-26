"""The final report as a background job. Each ``ReportQueue`` stands for one worker."""
import asyncio
import json

import fakeredis
import pytest
from fakeredis import FakeAsyncRedis
from starlette.testclient import TestClient

from app.api import interview_ws
from app.auth.interview_access import create_interview_access_token
from app.engine import report_jobs
from app.engine.engine import InterviewEngine
from app.engine.report_jobs import QUEUED_PREFIX, STREAM, ReportQueue, build_report
from app.services.v4_session_store import RedisV4SessionStore
from tests.conftest import (
    CONDUCTOR_TURN_JSON,
    EVALUATOR_JSON,
    GOVERNOR_JSON,
    STRATEGY_JSON,
    make_v4_state,
)

SID = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def server():
    return fakeredis.FakeServer()


def store_for(server):
    return RedisV4SessionStore(redis_client=fakeredis.FakeStrictRedis(server=server, decode_responses=True))


def redis_for(server):
    return FakeAsyncRedis(server=server, decode_responses=True)


def queue_for(server, builder=None):
    return ReportQueue(client=redis_for(server), builder=builder or (lambda sid: build_report(sid, store_for(server))))


@pytest.fixture
def llm(stub_llm, fake_evidence_repo, fake_repos):
    answer = json.dumps(EVALUATOR_JSON)
    turn = [answer, GOVERNOR_JSON, CONDUCTOR_TURN_JSON]
    stub = stub_llm(responses=[STRATEGY_JSON, "Question: First question?", *turn, answer])
    stub.repos = fake_repos
    return stub


async def reach_last_answer(server, queue):
    """A two-question interview, answered to the end on one worker."""
    store = store_for(server)
    engine = InterviewEngine(store=store, report_queue=queue)
    await engine.start_session(make_v4_state(session_id=SID, max_questions=2))
    for _ in range(4):
        response = await engine.process_answer(SID, "I added idempotency keys and a retry queue.")
        if response.get("interview_complete"):
            return engine, response
    raise AssertionError("the interview did not finish")


async def test_last_answer_returns_at_once_and_the_job_builds_the_report(server, llm):
    queue = queue_for(server)
    engine, response = await reach_last_answer(server, queue)
    assert response["type"] == "report_pending" and response["report_pending"] is True
    state = store_for(server).get(SID)
    assert state["report_pending"] and not state["finalized"]
    assert llm.repos["sessions"].completions == []
    calls_before_job = len(llm.calls)

    assert await queue.run_once() is True  # the group is created
    assert await queue.run_once() is True  # the job
    state = store_for(server).get(SID)
    assert state["finalized"] and not state["report_pending"] and state["hiring_decision"]
    assert len(llm.repos["sessions"].completions) == 1
    assert len(llm.calls) > calls_before_job
    assert await redis_for(server).xlen(STREAM) == 0
    assert await redis_for(server).exists(QUEUED_PREFIX + SID) == 0


async def test_running_the_job_twice_builds_one_report(server, llm):
    queue = queue_for(server)
    await reach_last_answer(server, queue)
    await build_report(SID, store_for(server))
    calls = len(llm.calls)
    await build_report(SID, store_for(server))
    assert len(llm.calls) == calls
    assert len(llm.repos["sessions"].completions) == 1
    assert len(llm.repos["messages"].answers) == 2  # each answer persisted once


async def test_a_repeated_submit_while_pending_is_not_scored(server, llm):
    queue = queue_for(server)
    engine, _ = await reach_last_answer(server, queue)
    calls, history = len(llm.calls), len(store_for(server).get(SID)["conversation_history"])
    again = await engine.process_answer(SID, "Sending it once more.")
    assert again["type"] == "report_pending"
    assert len(llm.calls) == calls
    assert len(store_for(server).get(SID)["conversation_history"]) == history
    assert await redis_for(server).xlen(STREAM) == 1  # not queued twice


async def test_without_redis_the_report_is_built_inline(server, llm):
    broken = fakeredis.FakeServer()
    broken.connected = False
    _, response = await reach_last_answer(server, ReportQueue(client=redis_for(broken)))
    assert response["interview_complete"] and "report_pending" not in response and "coverage" in response
    state = store_for(server).get(SID)
    assert state["finalized"] and not state["report_pending"]


async def test_a_failing_job_is_retried(server, monkeypatch):
    monkeypatch.setattr(report_jobs, "RETRY_DELAYS_S", (0, 0))
    attempts = []

    async def flaky(sid):
        attempts.append(sid)
        if len(attempts) < 3:
            raise RuntimeError("provider down")

    queue = queue_for(server, flaky)
    await queue.enqueue("s")
    await queue.run_once()
    await queue.run_once()
    assert attempts == ["s", "s", "s"] and await redis_for(server).xlen(STREAM) == 0


async def test_a_job_that_keeps_failing_is_given_up_and_can_be_queued_again(server, monkeypatch):
    monkeypatch.setattr(report_jobs, "RETRY_DELAYS_S", (0, 0))

    async def broken(sid):
        raise RuntimeError("always")

    queue = queue_for(server, broken)
    await queue.enqueue("s")
    await queue.run_once()
    await queue.run_once()
    redis = redis_for(server)
    assert await redis.xlen(STREAM) == 0 and await redis.exists(QUEUED_PREFIX + "s") == 0


async def test_another_worker_takes_over_a_job_whose_worker_died(server):
    done = []

    async def hang(sid):
        await asyncio.sleep(60)

    async def work(sid):
        done.append(sid)

    dying, survivor = queue_for(server, hang), queue_for(server, work)
    await dying.enqueue("s")
    await dying.run_once()  # creates the group
    task = asyncio.create_task(dying.run_once())
    await asyncio.sleep(0.05)
    task.cancel()  # the process goes away mid-job
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await survivor.run_once(claim_after_ms=60_000) is False  # not abandoned yet
    assert await survivor.run_once(claim_after_ms=0) is True
    assert done == ["s"]


async def test_consumer_picks_up_a_job_as_soon_as_it_is_queued(server):
    done = asyncio.Event()

    async def work(sid):
        done.set()

    queue = queue_for(server, work)
    queue.start()
    try:
        await asyncio.sleep(0.05)
        await queue.enqueue("s")
        await asyncio.wait_for(done.wait(), timeout=2)  # far below the sweep interval
    finally:
        await queue.stop()


async def test_the_worker_holding_the_socket_hears_that_the_report_is_ready(server, llm):
    builder_worker, socket_worker = queue_for(server), queue_for(server)
    await reach_last_answer(server, builder_worker)
    waiting = asyncio.create_task(
        socket_worker.wait_for_report(SID, store_for(server), timeout=20, check_every=15))
    await asyncio.sleep(0.1)
    await builder_worker.run_once()
    await builder_worker.run_once()
    state = await asyncio.wait_for(waiting, timeout=5)  # woken by the event, not by the 15 s re-read
    assert state["finalized"]


def test_websocket_sends_pending_then_pushes_report_ready(monkeypatch):
    from app.main import app

    finished = {"session_id": SID, "finalized": True, "hiring_recommendation": {"verdict": "hire"}}

    class FakeQueue:
        async def wait_for_report(self, sid, store):
            await asyncio.sleep(0.05)
            return finished

    class FakeEngine:
        def __init__(self, *a, report_queue=None, **k):
            assert report_queue is not None

        async def process_answer(self, sid, answer, integrity_meta=None):
            return {"type": "report_pending", "status": "completed", "interview_complete": True,
                    "report_pending": True, "session_id": sid}

    monkeypatch.setattr(interview_ws, "InterviewEngine", FakeEngine)
    monkeypatch.setattr(interview_ws, "active_queue_for", lambda store: FakeQueue())
    url = f"/ws/interview/{SID}?access={create_interview_access_token(SID)}"
    with TestClient(app).websocket_connect(url) as ws:
        ws.receive_json()
        ws.send_text(json.dumps({"type": "submit_answer", "candidate_answer": "done", "_id": "3"}))
        assert ws.receive_json()["phase"] == "evaluating"
        pending = ws.receive_json()
        ready = ws.receive_json()
    assert (pending["type"], pending["_id"]) == ("report_pending", "3")
    assert ready["type"] == "report_ready" and ready["session_id"] == SID and "_id" not in ready
