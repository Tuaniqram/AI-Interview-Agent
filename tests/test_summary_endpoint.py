"""Summary endpoint: engine extras must come from the durable
``interview_brain`` snapshot (DB), not the in-memory session store, so the
post-interview report survives restarts/evictions."""
from uuid import uuid4

import pytest

from app.api.interview_agent import _get_engine_summary, _get_legacy_summary
from app.models.db import InterviewBrain as InterviewBrainRecord

_FACTORY_SEAM = "app.api.interview_agent.get_session_factory"
_REPO_SEAM = "app.api.interview_agent.get_session_repo"
_MESSAGE_SEAM = "app.api.interview_agent.get_message_repo"
_EVAL_SEAM = "app.api.interview_agent.get_evaluation_repo"


class _ScalarResult:
    def __init__(self, row=None):
        self._row = row

    def scalar_one_or_none(self):
        return self._row


class FakeDB:
    def __init__(self, record=None):
        self.record = record

    async def execute(self, statement):
        return _ScalarResult(self.record)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _record(**overrides) -> InterviewBrainRecord:
    rec = InterviewBrainRecord(
        session_id=uuid4(),
        version=3,
        current_hypotheses=[
            {"status": "confirmed"},
            {"status": "refuted"},
            {"status": "testing"},
            {"status": "untested"},
        ],
        evidence_summary={
            "tech_core": {"evidence_count": 4, "average_score": 7.5, "gap": 0.1},
        },
        decision_state={
            "hiring_recommendation": {
                "verdict": "hire",
                "confidence": 0.7,
                "composite_score": 7.2,
            },
        },
        brain_metadata={"question_number": 6},
    )
    for k, v in overrides.items():
        setattr(rec, k, v)
    return rec


async def test_engine_summary_reads_brain_snapshot(monkeypatch):
    sid = str(uuid4())
    monkeypatch.setattr(_FACTORY_SEAM, lambda: lambda: FakeDB(_record()))

    data = await _get_engine_summary(sid)

    assert data["session_id"] == sid
    assert data["v4_verdict"] == "hire"
    assert data["v4_confidence"] == 0.7
    assert data["v4_composite_score"] == 7.2
    assert data["v4_evidence_count"] == 4
    assert data["v4_questions_asked"] == 6
    assert data["v4_competency_summary"]["tech_core"] == {
        "average_score": 7.5,
        "evidence_count": 4,
        "gap": 0.1,
    }
    assert data["v4_hypothesis_outcomes"] == {
        "confirmed": 1,
        "refuted": 1,
        "testing": 1,
        "untested": 1,
    }


async def test_engine_summary_empty_without_snapshot(monkeypatch):
    monkeypatch.setattr(_FACTORY_SEAM, lambda: lambda: FakeDB(None))

    assert await _get_engine_summary("session-1") == {}


async def test_engine_summary_degrades_on_db_error(monkeypatch):
    class BoomDB:
        async def execute(self, statement):
            raise RuntimeError("db down")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(_FACTORY_SEAM, lambda: BoomDB)

    assert await _get_engine_summary("session-1") == {}


def _fake_repo(session: dict) -> object:
    class _Repo:
        def __init__(self):
            self._session = session

        async def get_session(self, session_id):
            return self._session

        async def get_session_messages(self, session_id):
            return []

        async def get_evaluations(self, session_id):
            return []

    return _Repo()


@pytest.mark.asyncio
async def test_legacy_summary_survives_none_total_questions(monkeypatch):
    """V5 sessions have total_questions=NULL in the DB — the legacy summary
    must not 500 on the None comparison (regression: live demo run crashed
    with TypeError: '>' not supported between instances of 'NoneType' and 'int')."""
    sid = str(uuid4())
    session = {
        "session_id": sid,
        "total_questions": None,  # V5 sessions leave this NULL
        "status": "completed",
        "job_role": "Senior Frontend Engineer",
    }
    monkeypatch.setattr(_REPO_SEAM, lambda: _fake_repo(session))
    monkeypatch.setattr(_MESSAGE_SEAM, lambda: _fake_repo(session))
    monkeypatch.setattr(_EVAL_SEAM, lambda: _fake_repo(session))

    data = await _get_legacy_summary(sid)

    assert data["session_id"] == sid
    assert data["total_questions"] == 10  # falls back to the default
    assert data["answered_ratio"] == 0.0  # 0 answered / 10 possible, no crash
