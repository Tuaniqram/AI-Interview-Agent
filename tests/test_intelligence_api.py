"""V5 Intelligence API — bundle build endpoint + brain read endpoint.

The build endpoint is DB-best-effort: it returns the bundle even when
persistence fails, and test the /build path via a fake session.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.database.deps import get_db
from app.main import app


class _FakeScalars:
    def all(self):
        return []


class _FakeScalarResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return _FakeScalars()


class _FakeDB:
    """Captures adds; can be told to fail on commit."""

    def __init__(self, fail_on_commit=False):
        self.added = []
        self.fail_on_commit = fail_on_commit
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, stmt):
        return _FakeScalarResult(None)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self.fail_on_commit:
            raise RuntimeError("db down")
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_db():
    """Override get_db with a fake session; returns the fake."""
    _fake = _FakeDB()

    async def _provider():
        yield _fake

    app.dependency_overrides[get_db] = _provider
    yield _fake
    app.dependency_overrides.pop(get_db, None)


def _build_payload(**overrides):
    payload = {
        "job_role": "Backend Engineer",
        "use_rag": False,
        "use_llm": False,
        "candidate_profile": {
            "full_name": "Jane Doe",
            "skills": ["python", "postgresql"],
            "strengths": ["python"],
            "weaknesses": [],
        },
    }
    payload.update(overrides)
    return payload


def test_build_endpoint_returns_full_bundle(client):
    resp = client.post("/api/v1/intelligence/build", json=_build_payload())
    assert resp.status_code == 200
    bundle = resp.json()["intelligence"]
    assert set(bundle.keys()) == {
        "company_brain",
        "interview_blueprint",
        "candidate_brain",
        "initial_hypotheses",
        "evidence_requirements",
        "candidate_assessment",
        "aura_brain",
    }
    assert bundle["aura_brain"]["role_brain"]["mission"]
    assert "question_strategy" in bundle["aura_brain"]


def test_build_endpoint_uses_offline_fallbacks(client):
    resp = client.post("/api/v1/intelligence/build", json=_build_payload())
    bundle = resp.json()["intelligence"]
    assert bundle["company_brain"]["job_role"] == "Backend Engineer"
    assert bundle["candidate_brain"]["full_name"] == "Jane Doe"
    assert resp.json()["persisted"] is None


def test_build_persists_bundle_best_effort(client, fake_db):
    fake = fake_db
    resp = client.post(
        "/api/v1/intelligence/build",
        json=_build_payload(session_id=str(uuid.uuid4())),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["persisted"] is not None
    assert fake.added, "expected DB adds"
    types = {type(a).__name__ for a in fake.added}
    assert {"CompanyBrain", "InterviewBlueprint", "CandidateBrain"} <= types


def test_build_survives_persistence_failure(client, fake_db):
    fake = fake_db
    fake.fail_on_commit = True
    resp = client.post(
        "/api/v1/intelligence/build",
        json=_build_payload(session_id=str(uuid.uuid4())),
    )
    assert resp.status_code == 200
    assert resp.json()["intelligence"]["company_brain"]
    assert fake.rollbacks == 1


def test_build_validates_job_role(client):
    resp = client.post("/api/v1/intelligence/build", json={"job_role": ""})
    assert resp.status_code == 422


def test_brain_endpoint_returns_snapshot(client, fake_db):
    resp = client.get(f"/api/v1/intelligence/brain/{uuid.uuid4()}")
    assert resp.status_code == 200
    body = resp.json()
    assert "interview_brain" in body
    assert "evidence_graph" in body
    assert body["timeline"] == []
