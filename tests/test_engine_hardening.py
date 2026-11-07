"""Interview engine hardening: WebSocket authorization (deny by default), frame/answer
validation, rate limiting, per-session serialization, no leaked internals, idempotent
completion. No live services: the DB lookup and the engine are faked."""
import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth.interview_access import (
    INTERVIEW_ACCESS_TTL,
    create_interview_access_token,
    verify_interview_access_token,
)
from app.auth.jwt import ALGORITHM, create_access_token
from app.config import settings
from app.engine import guards
from app.api import interview_ws

SID = str(uuid.uuid4())
OTHER_SID = str(uuid.uuid4())


# ── guards: frames, answers, ids ─────────────────────────────────────────


@pytest.mark.parametrize("raw,fragment", [
    pytest.param(b"bytes", "text", id="bytes"),
    pytest.param("not json at all", "valid JSON", id="not-json"),
    pytest.param("[1, 2, 3]", "JSON object", id="array"),
    pytest.param("{}", "type is required", id="no-type"),
    pytest.param('{"type": 5}', "type is required", id="type-int"),
    pytest.param('{"type": ""}', "type is required", id="type-empty"),
    pytest.param("x" * (guards.MAX_FRAME_BYTES + 1), "too large", id="oversized"),
])
def test_parse_frame_rejects_bad_frames_without_raising(raw, fragment):
    data, error = guards.parse_frame(raw)
    assert data is None and fragment in error


def test_parse_frame_accepts_an_object_with_a_type():
    data, error = guards.parse_frame('{"type": "ping", "_id": "1"}')
    assert error is None and data["type"] == "ping"


def test_deeply_nested_json_does_not_crash_the_parser():
    data, error = guards.parse_frame("[" * 100000 + "]" * 100000)
    assert data is None and error


@pytest.mark.parametrize("value,ok", [
    ("A real answer", True),
    ("  padded  ", True),
    ("", False),
    ("   \n\t ", False),
    (None, False),
    (123, False),
    (["a"], False),
    pytest.param("x" * (guards.MAX_ANSWER_CHARS + 1), False, id="too-long"),
    pytest.param("x" * guards.MAX_ANSWER_CHARS, True, id="max-length"),
])
def test_validate_answer(value, ok):
    answer, error = guards.validate_answer(value)
    assert (error is None) is ok
    if ok:
        assert answer == value.strip()


def test_message_ids_are_only_echoed_when_small_scalars():
    assert guards.clean_message_id("abc") == "abc"
    assert guards.clean_message_id(7) == 7
    for bad in ({"a": 1}, ["x"], True, "x" * 65, None):
        assert guards.clean_message_id(bad) is None


def test_session_id_validation():
    assert guards.validate_session_id("abc") == "abc"
    for bad in ("", None, 5, "x" * 65):
        assert guards.validate_session_id(bad) is None


def test_rate_limiter_blocks_a_burst_then_recovers():
    rl = guards.MessageRateLimiter(max_messages=3, window_s=10)
    assert [rl.allow(now=t) for t in (0, 1, 2, 3)] == [True, True, True, False]
    assert rl.allow(now=11) is True  # the window slid past the old messages


async def test_session_lock_serializes_same_session_and_cleans_up():
    locks = guards.SessionLocks()
    running, peak = 0, 0

    async def step(sid):
        nonlocal running, peak
        async with locks.lock(sid):
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.02)
            running -= 1

    await asyncio.gather(*[step("a") for _ in range(5)])
    assert peak == 1  # never two steps of the same interview at once
    assert len(locks) == 0  # idle locks are dropped

    running, peak = 0, 0
    await asyncio.gather(step("a"), step("b"))
    assert peak == 2  # different interviews do not block each other


# ── per-session access tokens ────────────────────────────────────────────


def test_access_token_roundtrip_is_bound_to_one_session():
    token = create_interview_access_token(SID)
    assert verify_interview_access_token(token) == SID


def test_access_token_rejects_wrong_type_expired_tampered_and_garbage():
    candidate_jwt = create_access_token(SID, token_type="candidate_access")
    expired = jwt.encode(
        {"sub": SID, "type": "interview_access", "exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
        settings.SECRET_KEY, algorithm=ALGORITHM,
    )
    forged = jwt.encode({"sub": SID, "type": "interview_access", "exp": datetime.now(timezone.utc) + INTERVIEW_ACCESS_TTL},
                        "not-the-secret", algorithm=ALGORITHM)
    for bad in (candidate_jwt, expired, forged, "garbage", "", None):
        assert verify_interview_access_token(bad) is None


# ── authorization matrix ─────────────────────────────────────────────────


@pytest.fixture
def fake_db(monkeypatch):
    holder = SimpleNamespace(session=None)

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def execute(self, stmt):
            return SimpleNamespace(scalar_one_or_none=lambda: holder.session)

    monkeypatch.setattr(interview_ws, "get_session_factory", lambda: (lambda: _Ctx()))
    return holder


async def test_valid_access_token_for_this_session_is_allowed(fake_db):
    assert await interview_ws._verify_ws_session_access(SID, None, SID) is True


async def test_access_token_for_another_session_is_denied(fake_db):
    assert await interview_ws._verify_ws_session_access(SID, None, OTHER_SID) is False


async def test_no_credentials_is_denied_even_for_unowned_sessions(fake_db):
    fake_db.session = SimpleNamespace(candidate_profile_id=None)
    assert await interview_ws._verify_ws_session_access(SID, None, None) is False


async def test_owner_login_is_allowed_other_candidate_is_not(fake_db):
    owner = uuid.uuid4()
    fake_db.session = SimpleNamespace(candidate_profile_id=owner)
    assert await interview_ws._verify_ws_session_access(SID, str(owner), None) is True
    assert await interview_ws._verify_ws_session_access(SID, str(uuid.uuid4()), None) is False


async def test_logged_in_candidate_cannot_open_an_unowned_or_missing_session(fake_db):
    fake_db.session = SimpleNamespace(candidate_profile_id=None)
    assert await interview_ws._verify_ws_session_access(SID, str(uuid.uuid4()), None) is False
    fake_db.session = None
    assert await interview_ws._verify_ws_session_access(SID, str(uuid.uuid4()), None) is False


async def test_malformed_session_id_is_denied(fake_db):
    assert await interview_ws._verify_ws_session_access("not-a-uuid", str(uuid.uuid4()), None) is False


# ── WebSocket protocol through a real socket ─────────────────────────────


@pytest.fixture
def ws_env(monkeypatch):
    from app.main import app

    calls = SimpleNamespace(started=[], answers=[], fail_answer=None)

    async def fake_start(sid, notify=None):
        calls.started.append(sid)
        if notify is not None:  # the real start reports progress while it prepares the interview
            await notify("loading_context")
            await notify("planning_interview")
        return {"session_id": sid, "question": "Tell me about yourself", "question_number": 1}

    class FakeEngine:
        def __init__(self, *a, **k):
            pass

        async def process_answer(self, sid, answer, integrity_meta=None):
            if calls.fail_answer:
                raise calls.fail_answer
            calls.answers.append((sid, answer))
            return {"status": "in_progress", "question": "Next?", "question_number": 2}

    monkeypatch.setattr(interview_ws, "_start_v4_engine", fake_start)
    monkeypatch.setattr(interview_ws, "InterviewEngine", FakeEngine)
    return SimpleNamespace(client=TestClient(app), calls=calls)


def _connect(env, sid=SID, access=None, token=None):
    qs = []
    if access:
        qs.append(f"access={access}")
    if token:
        qs.append(f"token={token}")
    url = f"/ws/interview/{sid}" + (("?" + "&".join(qs)) if qs else "")
    return env.client.websocket_connect(url)


def _send(ws, **msg):
    ws.send_text(json.dumps(msg))
    while True:
        reply = ws.receive_json()
        # skip progress pushes sent while an interview is being prepared
        if not (reply.get("type") == "status" and reply.get("phase") in ("loading_context", "planning_interview")):
            return reply


def test_connection_without_credentials_cannot_start_or_answer(ws_env):
    with _connect(ws_env) as ws:
        assert ws.receive_json()["type"] == "connected"
        for msg in ({"type": "start_interview"}, {"type": "submit_answer", "candidate_answer": "hi"},
                    {"type": "request_question"}, {"type": "get_status"}):
            reply = _send(ws, **msg)
            assert reply["type"] == "error" and "denied" in reply["detail"].lower(), msg
    assert ws_env.calls.started == [] and ws_env.calls.answers == []


def test_valid_access_token_can_run_the_interview(ws_env):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        reply = _send(ws, type="start_interview", _id="1")
        assert reply["type"] == "question" and reply["_id"] == "1"
        ws.send_text(json.dumps({"type": "submit_answer", "candidate_answer": "I built APIs", "_id": "2"}))
        assert ws.receive_json()["type"] == "status"          # evaluating
        assert ws.receive_json()["type"] == "status"          # question_ready
        assert ws.receive_json()["type"] == "evaluation"
    assert ws_env.calls.answers == [(SID, "I built APIs")]


def test_access_token_cannot_pivot_to_another_session(ws_env):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        reply = _send(ws, type="start_interview", session_id=OTHER_SID)
        assert reply["type"] == "error" and "denied" in reply["detail"].lower()
    assert ws_env.calls.started == []


def test_candidate_login_token_alone_does_not_open_a_session_it_does_not_own(ws_env, fake_db):
    fake_db.session = SimpleNamespace(candidate_profile_id=uuid.uuid4())
    stranger = create_access_token(str(uuid.uuid4()), token_type="candidate_access")
    with _connect(ws_env, token=stranger) as ws:
        ws.receive_json()
        reply = _send(ws, type="start_interview")
        assert reply["type"] == "error" and "denied" in reply["detail"].lower()


def test_owner_login_token_runs_their_interview(ws_env, fake_db):
    owner = uuid.uuid4()
    fake_db.session = SimpleNamespace(candidate_profile_id=owner)
    token = create_access_token(str(owner), token_type="candidate_access")
    with _connect(ws_env, token=token) as ws:
        ws.receive_json()
        assert _send(ws, type="start_interview")["type"] == "question"


def test_bad_frames_get_errors_and_the_connection_survives(ws_env):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        for raw in ("not json", "[1,2]", "{}", '{"type": 7}', "x" * (guards.MAX_FRAME_BYTES + 10)):
            ws.send_text(raw)
            reply = ws.receive_json()
            assert reply["type"] == "error", raw[:20]
        assert _send(ws, type="ping")["type"] == "pong"  # still alive after all of that


@pytest.mark.parametrize("answer", ["", "   ", None, 42, ["x"], pytest.param("x" * (guards.MAX_ANSWER_CHARS + 1), id="too-long")])
def test_invalid_answers_are_rejected_before_the_engine(ws_env, answer):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        reply = _send(ws, type="submit_answer", candidate_answer=answer)
        assert reply["type"] == "error"
    assert ws_env.calls.answers == []


def test_unknown_message_type_is_a_generic_error(ws_env):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        reply = _send(ws, type="drop_tables")
        assert reply == {"type": "error", "detail": "Unknown message type"}  # does not echo the input


def test_internal_errors_never_leak_to_the_client(ws_env):
    ws_env.calls.fail_answer = RuntimeError("postgres://user:secret@host/db exploded")
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        ws.send_text(json.dumps({"type": "submit_answer", "candidate_answer": "hello"}))
        assert ws.receive_json()["type"] == "status"
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert "secret" not in json.dumps(reply) and "postgres" not in json.dumps(reply)
        assert _send(ws, type="ping")["type"] == "pong"  # the session survives an engine failure


def test_message_flood_is_rate_limited(ws_env):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        replies = []
        for _ in range(guards.RATE_LIMIT_MESSAGES + 5):
            ws.send_text(json.dumps({"type": "ping"}))
            replies.append(ws.receive_json())
        limited = [r for r in replies if r["type"] == "error"]
        assert len(limited) >= 5 and "slow down" in limited[0]["detail"].lower()


def test_oversized_message_id_is_not_echoed(ws_env):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        reply = _send(ws, type="ping", _id="x" * 500)
        assert reply["type"] == "pong" and "_id" not in reply


def test_connection_registry_is_cleaned_up_on_disconnect(ws_env):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        assert SID in interview_ws._connections
    assert SID not in interview_ws._connections


# ── engine: completion is idempotent ─────────────────────────────────────


async def test_answer_after_completion_returns_the_report_without_rescoring(monkeypatch):
    from app.engine.engine import InterviewEngine
    from tests.conftest import make_v4_state

    state = make_v4_state(session_id=SID, finalized=True, question_number=5, max_questions=5,
                          hiring_decision={"decision": "no_hire"}, evaluation_score=6.1)

    class Store:
        def get_or_raise(self, sid):
            return dict(state)

    async def must_not_run(*a, **k):
        raise AssertionError("a finished interview must not be evaluated again")

    monkeypatch.setattr("app.agents.evaluation.candidate_evaluator.unified_evaluator_node", must_not_run)
    monkeypatch.setattr("app.engine.decision.finalize_session", must_not_run)

    report = await InterviewEngine(store=Store(), event_log=SimpleNamespace()).process_answer(SID, "late answer")

    assert report["interview_complete"] is True
    assert report["status"] == "completed"


# ── engine: blocking store I/O stays off the event loop ──────────────────


async def test_store_io_runs_blocking_calls_off_the_event_loop():
    import threading

    from app.engine.store_io import store_checkpoint, store_get, store_get_or_raise

    loop_thread = threading.get_ident()
    seen = {}

    class Store:
        def get(self, sid):
            seen["get"] = threading.get_ident()
            return {"sid": sid}

        def get_or_raise(self, sid):
            seen["get_or_raise"] = threading.get_ident()
            return {"sid": sid}

        def checkpoint(self, sid, state):
            seen["checkpoint"] = threading.get_ident()

    store = Store()
    assert await store_get(store, "s") == {"sid": "s"}
    assert await store_get_or_raise(store, "s") == {"sid": "s"}
    await store_checkpoint(store, "s", {})
    assert set(seen) == {"get", "get_or_raise", "checkpoint"}
    assert all(t != loop_thread for t in seen.values())  # a slow DB can no longer freeze every user


async def test_store_errors_still_propagate_through_the_thread_hop():
    from app.engine.store_io import store_get_or_raise
    from app.exceptions import SessionNotFoundException

    class Store:
        def get_or_raise(self, sid):
            raise SessionNotFoundException(sid)

    with pytest.raises(SessionNotFoundException):
        await store_get_or_raise(Store(), "missing")


def test_start_pushes_progress_frames_before_the_question(ws_env):
    with _connect(ws_env, access=create_interview_access_token(SID)) as ws:
        ws.receive_json()
        ws.send_text(json.dumps({"type": "start_interview", "_id": "7"}))
        frames = [ws.receive_json() for _ in range(3)]
    assert [f["type"] for f in frames] == ["status", "status", "question"]
    assert [f.get("phase") for f in frames[:2]] == ["loading_context", "planning_interview"]
    assert "_id" not in frames[0] and "_id" not in frames[1]  # pushes never look like the awaited reply
    assert frames[2]["_id"] == "7"
