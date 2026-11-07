"""WebSocket v4/AURA protocol tests.

Drives the real WS endpoint with the real v4 nodes; LLM + DB side effects are
stubbed (StubLLM, FakeStore, fake DB row). Verifies the protocol contract:
_id echo, start → question, answer → status pushes + evaluation, get_status.
"""
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.interview_ws import router as ws_router
from tests.conftest import (
    CONDUCTOR_TURN_JSON,
    EVALUATOR_JSON,
    GOVERNOR_JSON,
    STRATEGY_JSON,
    make_v4_state,
)


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(ws_router)
    with TestClient(app) as c:
        yield c


class FakeStore:
    def __init__(self):
        self.data = {}

    def get(self, session_id: str):
        return self.data.get(session_id)

    def get_or_raise(self, session_id: str) -> dict:
        if session_id not in self.data:
            raise KeyError(session_id)
        return self.data[session_id]

    def set(self, session_id: str, state: dict) -> None:
        self.data[session_id] = state

    def pop(self, session_id: str) -> dict | None:
        return self.data.pop(session_id, None)

    def checkpoint(self, session_id: str, state: dict) -> None:
        self.data[session_id] = state

    def list_active(self):
        return []

    def count(self):
        return len(self.data)


PROGRESS_PHASES = {"loading_context", "planning_interview"}


def _receive_skipping_progress(ws):
    """Preparing an interview pushes status frames before the question reply; skip those."""
    while True:
        msg = ws.receive_json()
        if not (msg.get("type") == "status" and msg.get("phase") in PROGRESS_PHASES):
            return msg


def _ws_url(session_id: str) -> str:
    """The socket denies by default: connect with the per-session access token."""
    from app.auth.interview_access import create_interview_access_token

    return f"/ws/interview/{session_id}?access={create_interview_access_token(session_id)}"


class FakeRow:
    def __init__(self, session_id):
        self.id = uuid4()
        self.job_role = "Software Engineer"
        self.job_role_snapshot = "Software Engineer"
        self.org_id = None
        self.it_role_id = uuid4()
        self.department_id = None
        self.scorecard_template_id = None
        self.candidate_profile_id = None
        self.used = False


@pytest.fixture
def ws_env(monkeypatch, fake_repos):
    store = FakeStore()
    row = FakeRow(None)

    async def fake_load(session_id):
        row.id = uuid4()
        row.used = True
        return row

    monkeypatch.setattr("app.api.interview_ws._load_db_session_row", fake_load)
    monkeypatch.setattr("app.api.interview_ws.get_v4_session_store", lambda: store)

    class NoopPersister:
        async def save_snapshot(self, brain):
            return None

    monkeypatch.setattr("app.api.interview_ws._get_v5_persister", lambda: NoopPersister())

    # Taxonomy resolution talks to the database (role catalog) and, failing that, the LLM profiler:
    # stub it so these protocol tests stay offline and their scripted LLM replies line up.
    class _NoDb:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    async def fake_resolve(db, **kwargs):
        from app.data.competency_resolver import default_taxonomy

        return default_taxonomy()

    monkeypatch.setattr("app.api.interview_ws.get_session_factory", lambda: (lambda: _NoDb()))
    monkeypatch.setattr("app.api.interview_ws.resolve_competencies", fake_resolve)
    return store, row


def test_ws_full_cycle(ws_env, client, stub_llm, fake_evidence_repo, fake_repos, stub_intelligence):
    stub_llm(responses=[
        STRATEGY_JSON,                 # strategy_brain (start)
        CONDUCTOR_TURN_JSON,           # question_generator conductor turn (start)
        json_dumps(EVALUATOR_JSON),    # unified_evaluator (answer)
        GOVERNOR_JSON,                 # difficulty_governor (answer)
        CONDUCTOR_TURN_JSON,           # question_generator conductor turn (answer)
    ])

    session_id = str(uuid4())
    with client.websocket_connect(_ws_url(session_id)) as ws:
            connected = ws.receive_json()
            assert connected["type"] == "connected"

            # ── start ──
            ws.send_json({"_id": "1", "type": "start_interview"})
            question_msg = _receive_skipping_progress(ws)
            assert question_msg["_id"] == "1"
            assert question_msg["type"] == "question"
            assert question_msg["question"]["text"]
            assert question_msg["conversation_turn"]
            assert question_msg["job_role"] == "Software Engineer"
            assert question_msg["department_id"] is None

            # ── answer ──
            ws.send_json({"_id": "2", "type": "submit_answer", "candidate_answer": "I build distributed systems."})
            evaluating = ws.receive_json()
            assert evaluating["type"] == "status"
            assert evaluating["phase"] == "evaluating"
            question_ready = ws.receive_json()
            assert question_ready["type"] == "status"
            assert question_ready["phase"] == "question_ready"
            evaluation = ws.receive_json()
            assert evaluation["_id"] == "2"
            assert evaluation["type"] == "evaluation"
            assert evaluation["evaluation"]["scores"]
            assert evaluation["next_question"]["text"]
            assert evaluation["conversation_turn"]

            # ── status ──
            ws.send_json({"_id": "3", "type": "get_status"})
            snapshot = ws.receive_json()
            assert snapshot["_id"] == "3"
            assert snapshot["type"] == "status_snapshot"
            assert snapshot["current_question"]

            # ── write-back: one evaluated turn persisted per answered question ──
            assert len(fake_repos["messages"].questions) == 1
            assert len(fake_repos["messages"].answers) == 1
            assert len(fake_repos["evaluations"].saved) == 1
            persisted = fake_repos["evaluations"].saved[0]
            # Deterministic explainable composite (Phase 4) — not the raw LLM score.
            # AURA enables evaluator calibration, which the engine applies before
            # reconciling — mirror the real scoring path so the expectation holds.
            from app.agents.evaluation.scoring import _apply_evaluator_calibration, reconcile_composite
            from app.config.interview_styles import get_style

            expected_composite, _ = reconcile_composite(
                _apply_evaluator_calibration(EVALUATOR_JSON),
                weights=get_style("AURA").get("evaluator_weights"),
            )
            assert persisted["overall_score"] == pytest.approx(expected_composite)
            assert persisted["technical_score"] == pytest.approx(8.0)
            assert persisted["communication_score"] == pytest.approx(7.0)
            assert "a" in persisted["strengths"]
            assert "b" in persisted["weaknesses"]
            assert persisted["message_id"] == fake_repos["messages"].answers[0]["id"]


def test_ws_start_full_boot_when_store_preseeded(ws_env, client, stub_llm, fake_evidence_repo, fake_repos, stub_intelligence):
    """A fresh REST seed (no nodes executed yet) must still run the full
    engine boot — company brain, taxonomy, resume, strategy, first question —
    instead of short-circuiting on the seed dict."""
    store, row = ws_env
    session_id = str(uuid4())
    seed = make_v4_state(session_id=session_id)
    seed["question_number"] = 0
    seed["current_question"] = ""
    seed["nodes_executed"] = []
    store.set(session_id, seed)

    stub_llm(responses=[
        STRATEGY_JSON,       # strategy_brain (start)
        CONDUCTOR_TURN_JSON, # question_generator conductor turn (start)
    ])

    with client.websocket_connect(_ws_url(session_id)) as ws:
        ws.receive_json()  # connected
        ws.send_json({"_id": "1", "type": "start_interview"})
        question_msg = _receive_skipping_progress(ws)
        assert question_msg["_id"] == "1"
        assert question_msg["type"] == "question"
        assert question_msg["question"]["text"]
        assert question_msg["conversation_turn"]
        assert question_msg["status"] == "in_progress"

    # The engine must have replaced the empty seed with a real started state.
    booted = store.get(session_id)
    assert booted is not None
    assert booted["current_question"]
    assert booted["question_number"] >= 1
    assert booted["nodes_executed"], "full boot chain should have run (not the early return)"


def test_ws_start_resumes_started_session_without_llm(ws_env, client, stub_llm, fake_evidence_repo, fake_repos, stub_intelligence):
    """A store entry that has already started (question_number > 0) is resumed
    via build_start_response — no intelligence build, no LLM calls."""
    store, row = ws_env
    session_id = str(uuid4())
    seed = make_v4_state(session_id=session_id)
    seed["question_number"] = 3
    seed["current_question"] = "Resume point question?"
    seed["nodes_executed"] = ["strategy_brain", "question_generator"]
    store.set(session_id, seed)

    stub_llm(responses=[])

    with client.websocket_connect(_ws_url(session_id)) as ws:
        ws.receive_json()  # connected
        ws.send_json({"_id": "1", "type": "start_interview"})
        question_msg = _receive_skipping_progress(ws)
        assert question_msg["_id"] == "1"
        assert question_msg["type"] == "question"
        assert question_msg["question"]["text"] == "Resume point question?"


def json_dumps(obj):
    import json
    return json.dumps(obj)
