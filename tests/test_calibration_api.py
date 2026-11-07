"""Calibration API — feedback record + drift report (contract, fake DB)."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth.middleware import authenticate
from app.database.deps import get_db
from app.main import app
from app.models.db import CalibrationFeedback


pytestmark = pytest.mark.skip(
    reason="Calibration API removed in the IT-only schema: calibration_feedback table dropped, router not mounted"
)


class _FakeUser:
    id = uuid.uuid4()
    is_admin = True
    is_active = True


class _FakeScalarResult:
    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _FakeScalars(self._values)


class _FakeDB:
    """Scriptable async session: each execute pops the next queued result."""

    def __init__(self, queue=None):
        self._queue = list(queue or [])
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        if self._queue:
            return self._queue.pop(0)
        return _FakeScalarResult(None)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass


class _FakeSession:
    def __init__(self, status="completed"):
        self.id = uuid.uuid4()
        self.org_id = uuid.uuid4()
        self.department_id = 7
        self.job_role = "Marketing Manager"
        self.status = status


class _FakeBrain:
    brain_metadata = {
        "calibration_state": {
            "calibrated_verdict": "hire",
            "calibrated_score": 7.6,
            "difficulty_reached": 4,
            "role_floor": 3,
        },
        "difficulty_state": {"difficulty_reached": 4, "role_floor": 3},
    }


def _feedback_row(**overrides):
    row = {
        "job_role": "Marketing Manager",
        "predicted_verdict": "hire",
        "predicted_score": 7.6,
        "difficulty_reached": 4,
        "role_floor": 3,
        "actual_outcome": "strong_performance",
    }
    row.update(overrides)
    return type("Row", (), row)()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_env():
    async def _auth():
        return _FakeUser()

    app.dependency_overrides[authenticate] = _auth

    def _use_db(fake: _FakeDB):
        async def _provider():
            yield fake

        app.dependency_overrides[get_db] = _provider
        return fake

    yield _use_db
    for key in (authenticate, get_db):
        app.dependency_overrides.pop(key, None)


def test_put_feedback_snapshots_predictions(client, fake_env):
    org_id = uuid.uuid4()
    session_id = uuid.uuid4()
    fake = fake_env(
        _FakeDB(queue=[
            _FakeScalarResult(_FakeSession()),
            _FakeScalarResult(_FakeBrain()),
            _FakeScalarResult(None),
        ])
    )
    resp = client.put(
        f"/api/v1/orgs/{org_id}/calibration/feedback/{session_id}",
        json={"actual_outcome": "met_expectations", "notes": "solid ramp-up"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == str(session_id)
    assert body["predicted_verdict"] == "hire"
    assert body["predicted_score"] == 7.6
    assert body["actual_outcome"] == "met_expectations"
    assert body["recorded"] is True
    assert fake.commits == 1
    assert any(isinstance(a, CalibrationFeedback) for a in fake.added)


def test_put_feedback_updates_existing_row(client, fake_env):
    org_id = uuid.uuid4()
    session_id = uuid.uuid4()
    existing = CalibrationFeedback(
        session_id=uuid.UUID(str(session_id)), actual_outcome="no_feedback"
    )
    fake = fake_env(
        _FakeDB(queue=[
            _FakeScalarResult(_FakeSession()),
            _FakeScalarResult(_FakeBrain()),
            _FakeScalarResult(existing),
        ])
    )
    resp = client.put(
        f"/api/v1/orgs/{org_id}/calibration/feedback/{session_id}",
        json={"actual_outcome": "below_expectations"},
    )
    assert resp.status_code == 200
    assert resp.json()["actual_outcome"] == "below_expectations"
    assert fake.added == []  # updated, not re-added


def test_put_feedback_404_when_session_not_in_org(client, fake_env):
    fake_env(_FakeDB(queue=[_FakeScalarResult(None)]))
    resp = client.put(
        f"/api/v1/orgs/{uuid.uuid4()}/calibration/feedback/{uuid.uuid4()}",
        json={"actual_outcome": "met_expectations"},
    )
    assert resp.status_code == 404


def test_put_feedback_400_when_session_not_completed(client, fake_env):
    fake_env(_FakeDB(queue=[_FakeScalarResult(_FakeSession(status="active"))]))
    resp = client.put(
        f"/api/v1/orgs/{uuid.uuid4()}/calibration/feedback/{uuid.uuid4()}",
        json={"actual_outcome": "met_expectations"},
    )
    assert resp.status_code == 400


def test_put_feedback_422_on_invalid_outcome(client, fake_env):
    fake_env(_FakeDB())
    resp = client.put(
        f"/api/v1/orgs/{uuid.uuid4()}/calibration/feedback/{uuid.uuid4()}",
        json={"actual_outcome": "not-an-outcome"},
    )
    assert resp.status_code == 422


def test_get_drift_report_shape(client, fake_env):
    org_id = uuid.uuid4()
    fake_env(
        _FakeDB(queue=[
            _FakeScalarsResult([
                _feedback_row(),
                _feedback_row(
                    job_role="Finance Analyst",
                    predicted_verdict="no_hire",
                    actual_outcome="below_expectations",
                ),
            ])
        ])
    )
    resp = client.get(f"/api/v1/orgs/{org_id}/calibration/drift")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"overall", "by_family", "by_difficulty_band", "insights"}
    assert body["overall"]["total"] == 2
    assert body["by_family"]["marketing"]["total"] == 1
    assert body["by_family"]["finance"]["correct"] == 1
    assert body["by_difficulty_band"]["0.1-0.3"]["total"] == 2


def test_get_drift_summary_headline(client, fake_env):
    org_id = uuid.uuid4()
    fake_env(
        _FakeDB(queue=[
            _FakeScalarsResult([
                _feedback_row(actual_outcome="strong_performance"),
                _feedback_row(actual_outcome="no_feedback"),
            ])
        ])
    )
    resp = client.get(f"/api/v1/orgs/{org_id}/calibration/drift/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tracked_sessions"] == 2
    assert body["awaiting_feedback"] == 1
