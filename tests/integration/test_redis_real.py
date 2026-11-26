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
