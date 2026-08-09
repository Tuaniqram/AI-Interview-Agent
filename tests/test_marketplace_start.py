"""Public (marketplace listing) interview start must seed the same v4 engine state
as the practice start path."""
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.marketplace.schemas import StartInterviewRequest
from app.marketplace.service import start_public_interview
from app.models.db import CandidateProfile, InterviewTemplate, PublicInterview
from app.services.v4_session_store import get_v4_session_store


class _FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDB:
    def __init__(self, public_interview):
        self.public_interview = public_interview
        self.added = []
        self.flushed = 0
        self.committed = 0

    async def execute(self, stmt):
        entity = stmt.column_descriptions[0]["entity"]
        if entity is PublicInterview:
            if self.public_interview is None or not self.public_interview.is_open:
                return _FakeScalarResult(None)
            return _FakeScalarResult(self.public_interview)
        return _FakeScalarResult(None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed += 1

    async def commit(self):
        self.committed += 1


def _fake_listing():
    return SimpleNamespace(
        id="pi-1",
        is_open=True,
        template_id=None,
        org_id="org-1",
        department_id=None,
        title="Backend Engineer",
        interview_mode="text",
        style_name="STANDARD",
    )


async def test_start_public_interview_seeds_v4_state(monkeypatch):
    store = get_v4_session_store()
    db = _FakeDB(_fake_listing())
    req = StartInterviewRequest(candidate_email="a@b.com", candidate_name="Alice")
    async def fake_resolve_competencies(db, scorecard_template_id=None, department_id=None, role_context=None):
        return []

    monkeypatch.setattr("app.marketplace.service.resolve_competencies", fake_resolve_competencies)

    resp = await start_public_interview("pi-1", req, db)

    assert db.committed == 1
    assert len(db.added) == 2  # InterviewSession + PublicInterviewSubmission

    state = store.get_or_raise(str(resp.session_id))
    assert state["flow_type"] == "v4_evidence_driven"
    assert state["job_role"] == "Backend Engineer"
    assert state["session_id"] == str(resp.session_id)
    assert state["candidate_profile"]["full_name"] == "Alice"
    assert state["evaluator_mode"] == "unified"
    assert state["question_number"] == 0
    assert state["conversation_history"] == []


async def test_start_public_interview_404_when_closed():
    db = _FakeDB(_fake_listing())
    db.public_interview.is_open = False

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await start_public_interview(
            "pi-1",
            StartInterviewRequest(candidate_email="a@b.com", candidate_name="Alice"),
            db,
        )
    assert exc.value.status_code == 404
