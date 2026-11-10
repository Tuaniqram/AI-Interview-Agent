"""The interview report must carry the candidate and organization context."""
import uuid
from types import SimpleNamespace

import pytest

from app.api.interview_agent import _report_context


class _Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        return self.value


class _FakeDB:
    def __init__(self, ids, candidate=None, org_name=None):
        self._queue = [ids, candidate]
        self._org_name = org_name

    async def execute(self, _stmt):
        return _Result(self._queue.pop(0))

    async def scalar(self, _stmt):
        return self._org_name


class _FakeFactory:
    def __init__(self, db):
        self._db = db

    def __call__(self):
        db = self._db

        class _Context:
            async def __aenter__(self):
                return db

            async def __aexit__(self, *exc):
                return False

        return _Context()


@pytest.mark.asyncio
async def test_report_context_includes_candidate_and_organization(monkeypatch):
    candidate = SimpleNamespace(name="Amina Yusuf", email="amina@example.com")
    db = _FakeDB(ids=(uuid.uuid4(), uuid.uuid4()), candidate=candidate, org_name="GulfTex")
    monkeypatch.setattr("app.api.interview_agent.get_session_factory", lambda: _FakeFactory(db))

    context = await _report_context(str(uuid.uuid4()))

    assert context == {
        "candidate_name": "Amina Yusuf",
        "candidate_email": "amina@example.com",
        "org_name": "GulfTex",
    }


@pytest.mark.asyncio
async def test_report_context_handles_missing_session(monkeypatch):
    db = _FakeDB(ids=None)
    monkeypatch.setattr("app.api.interview_agent.get_session_factory", lambda: _FakeFactory(db))

    assert await _report_context(str(uuid.uuid4())) == {}
