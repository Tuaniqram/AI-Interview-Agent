"""Unit tests for the single-worker behaviour of RedisV4SessionStore (fakeredis, no live Redis).

What several workers need from it is in ``test_shared_session_store.py``.
"""

import fakeredis
import pytest

from app.exceptions import SessionNotFoundException
from app.services.v4_session_store import RedisV4SessionStore


@pytest.fixture
def redis_store():
    return RedisV4SessionStore(redis_client=fakeredis.FakeStrictRedis(decode_responses=True))


def _state(n: int, version: int = 0) -> dict:
    return {"session_id": f"test{n}", "difficulty_level": 1, "question_number": 0, "store_version": version}


def test_set_then_get(redis_store):
    assert redis_store.set("sess-1", _state(1)) == 1
    assert redis_store.get("sess-1") == _state(1, version=1)


def test_get_or_raise_missing(redis_store):
    with pytest.raises(SessionNotFoundException):
        redis_store.get_or_raise("nope")


def test_get_miss_returns_none(redis_store):
    assert redis_store.get("ghost") is None


def test_each_write_raises_the_version(redis_store):
    assert redis_store.set("v", _state(1)) == 1
    assert redis_store.set("v", _state(2, version=1)) == 2
    assert redis_store.get("v") == _state(2, version=2)


def test_pop_deletes_and_returns(redis_store):
    redis_store.set("sess-pop", _state(1))
    assert redis_store.pop("sess-pop")["session_id"] == "test1"
    assert redis_store.get("sess-pop") is None


def test_pop_missing_returns_none(redis_store):
    assert redis_store.pop("nope") is None


def test_works_without_redis_or_database():
    store = RedisV4SessionStore()  # REDIS_URL and DATABASE_URL are blank in tests
    store.set("sess-degenerate", _state(1))
    assert store.get("sess-degenerate") == _state(1, version=1)
    assert store.pop("sess-degenerate") is not None


def test_count_counts_only_sessions(redis_store):
    redis_store.set("a", _state(1))
    redis_store.set("b", _state(2))
    redis_store._client.set("aura:rl:x", "1")
    assert redis_store.count() == 2


def test_list_active_scans_keys(redis_store):
    redis_store.set("a", _state(1))
    redis_store.set("b", _state(2))
    assert sorted(row["session_id"] for row in redis_store.list_active()) == ["a", "b"]


def test_list_active_empty(redis_store):
    assert redis_store.list_active() == []


def test_checkpoint_does_not_raise_without_db(redis_store):
    redis_store.set("a", _state(1))
    redis_store.checkpoint("a", _state(1, version=1))


def test_close_releases_the_client(redis_store):
    redis_store.set("a", _state(1))
    redis_store.close()
    assert redis_store._client is None
    assert redis_store.get("a") is None
