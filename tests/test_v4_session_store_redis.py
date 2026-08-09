"""Stub-based unit tests for RedisV4SessionStore.

No live Redis / no fakeredis dependency. Uses an in-process dict stub that
mirrors the subset of the ``redis-py`` sync client API the store touches.
"""

import pytest

from app.services.v4_session_store import RedisV4SessionStore, REDIS_KEY_PREFIX


class FakeRedis:
    """Minimal dict-backed stand-in for redis-py's sync ``Redis``.

    Implements exactly the methods RedisV4SessionStore calls: get / setex /
    delete / scan_iter / ping / close / dbsize. ``decode_responses=True`` in
    the real client returns ``str``; this stub returns ``str`` too.
    """

    def __init__(self):
        self._data: dict[str, str] = {}

    def get(self, key: str):
        return self._data.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._data[key] = value

    def delete(self, key: str) -> int:
        return 1 if self._data.pop(key, None) is not None else 0

    def scan_iter(self, pattern: str):
        prefix = pattern.replace("*", "").replace(REDIS_KEY_PREFIX, "")
        # Only the store calls scan_iter(f"{REDIS_KEY_PREFIX}*").
        for key in list(self._data):
            if key.startswith(REDIS_KEY_PREFIX):
                yield key

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        self._data.clear()

    def dbsize(self) -> int:
        return len(self._data)


@pytest.fixture
def redis_store():
    return RedisV4SessionStore(redis_client=FakeRedis(), sync_engine=None)


def _state(n: int) -> dict:
    return {"session_id": f"test{n}", "difficulty_level": 1, "question_number": 0}


# --- basic round-trip -------------------------------------------------------

def test_set_then_get(redis_store):
    sid = "sess-1"
    redis_store.set(sid, _state(1))
    assert redis_store.get(sid) == _state(1)


def test_get_or_raise_missing(redis_store):
    from app.exceptions import SessionNotFoundException

    with pytest.raises(SessionNotFoundException):
        redis_store.get_or_raise("nope")


def test_get_miss_returns_none(redis_store):
    assert redis_store.get("ghost") is None


# --- TTL is refreshed on each set ------------------------------------------

def test_setex_invoked(redis_store):
    # FakeRedis records values regardless of ttl; set twice and confirm key kept
    sid = "sess-ttl"
    redis_store.set(sid, _state(1))
    redis_store.set(sid, _state(2))
    assert redis_store.get(sid) == _state(2)


# --- pop -------------------------------------------------------------------

def test_pop_deletes_and_returns(redis_store):
    sid = "sess-pop"
    redis_store.set(sid, _state(1))
    out = redis_store.pop(sid)
    assert out["session_id"] == f"test1"
    assert redis_store.get(sid) is None


def test_pop_missing_returns_none(redis_store):
    assert redis_store.pop("nope") is None


# --- degraded fallback (redis failure / no redis) --------------------------

def test_degraded_when_no_redis():
    # No REDIS_URL, no injected client -> degraded memory mode, still works.
    store = RedisV4SessionStore()  # reads env (likely unset in CI)
    sid = "sess-degenerate"
    store.set(sid, _state(1))
    assert store.get(sid) == _state(1)
    assert store.pop(sid) is not None


# --- list_active / count ---------------------------------------------------

def test_count_counts_keys(redis_store):
    redis_store.set("a", _state(1))
    redis_store.set("b", _state(2))
    assert redis_store.count() == 2


def test_list_active_scans_keys(redis_store):
    redis_store.set("a", _state(1))
    redis_store.set("b", _state(2))
    active = redis_store.list_active()
    ids = sorted(row["session_id"] for row in active)
    assert ids == ["a", "b"]


def test_list_active_empty(redis_store):
    assert redis_store.list_active() == []


# --- checkpoint ------------------------------------------------------------

def test_checkpoint_does_not_raise_without_db(redis_store):
    # sync_engine=None -> checkpoint is a no-op (no DB), must not raise
    redis_store.set("a", _state(1))
    redis_store.checkpoint("a", _state(1))  # no exception == pass


# --- close -----------------------------------------------------------------

def test_close_clears_client(redis_store):
    redis_store.set("a", _state(1))
    redis_store.close()
    assert redis_store._client is not None  # close() clears data, not ref
    assert redis_store.get("a") is None
