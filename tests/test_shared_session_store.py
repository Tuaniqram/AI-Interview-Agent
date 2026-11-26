"""Session state shared by several worker processes.

Each ``RedisV4SessionStore`` below stands for one worker: its own client, its own memory, one shared
Redis server (fakeredis) and one shared durable table (an in-memory stand-in for Postgres).
"""
import json

import fakeredis
import pytest

from app.engine.engine import InterviewEngine
from app.exceptions import StaleSessionError
from app.services.v4_session_store import REDIS_KEY_PREFIX, RedisV4SessionStore
from tests.conftest import (
    CONDUCTOR_TURN_JSON,
    EVALUATOR_JSON,
    GOVERNOR_JSON,
    STRATEGY_JSON,
    make_v4_state,
)


class FakeDurable:
    """``PostgresCheckpoint`` in memory, with the same accept/refuse rule."""

    def __init__(self):
        self.rows: dict[str, str] = {}
        self.down = False

    def _check(self):
        if self.down:
            raise ConnectionError("database down")

    def load(self, sid):
        return self.load_if_newer(sid, -1)

    def load_if_newer(self, sid, version):
        self._check()
        raw = self.rows.get(sid)
        if raw is None:
            return None
        state = json.loads(raw)
        return state if int(state.get("store_version") or 0) > version else None

    def upsert_if_newer(self, sid, state, version):
        self._check()
        raw = self.rows.get(sid)
        if raw is not None:
            stored = json.loads(raw)
            if int(stored.get("store_version") or 0) >= version and stored != json.loads(json.dumps(state)):
                return False
        self.rows[sid] = json.dumps(state)
        return True

    def delete(self, sid):
        self.rows.pop(sid, None)


class Cluster:
    def __init__(self):
        self.server = fakeredis.FakeServer()
        self.durable = FakeDurable()

    def worker(self, durable=True) -> RedisV4SessionStore:
        client = fakeredis.FakeStrictRedis(server=self.server, decode_responses=True)
        return RedisV4SessionStore(redis_client=client, durable=self.durable if durable else None)

    def redis_down(self):
        self.server.connected = False

    def redis_up(self, *workers):
        self.server.connected = True
        for w in workers:  # the real store retries on its own after a few seconds
            w._breaker.reset()


@pytest.fixture
def cluster():
    return Cluster()


def advance(store, sid):
    """One turn on one worker: read, move on one question, write, checkpoint."""
    state = store.get_or_raise(sid)
    state["question_number"] += 1
    state["store_version"] = store.set(sid, state)
    store.checkpoint(sid, state)
    return state["question_number"]


def start(store, sid="s1"):
    state = {"session_id": sid, "question_number": 1}
    state["store_version"] = store.set(sid, state)
    store.checkpoint(sid, state)


def test_alternating_workers_never_go_backwards(cluster):
    a, b = cluster.worker(), cluster.worker()
    start(a)
    seen = [advance(a, "s1"), advance(b, "s1"), advance(a, "s1"), advance(b, "s1")]
    assert seen == [2, 3, 4, 5]
    assert a.get("s1")["question_number"] == b.get("s1")["question_number"] == 5
    assert a.get("s1")["store_version"] == 5


def test_a_write_from_an_old_read_is_refused(cluster):
    a, b = cluster.worker(), cluster.worker()
    start(a)
    old = a.get("s1")
    advance(b, "s1")
    old["question_number"] = 99
    with pytest.raises(StaleSessionError):
        a.set("s1", old)
    assert a.get("s1")["question_number"] == 2


def test_redis_down_reads_the_database_every_time(cluster):
    a, b = cluster.worker(), cluster.worker()
    start(a)
    cluster.redis_down()
    assert a.get("s1")["question_number"] == 1
    assert advance(b, "s1") == 2
    assert a.get("s1")["question_number"] == 2  # not the copy A read a moment ago
    assert advance(a, "s1") == 3
    assert b.get("s1")["question_number"] == 3


def test_redis_back_after_an_outage_does_not_serve_its_old_copy(cluster):
    a, b = cluster.worker(), cluster.worker()
    start(a)
    cluster.redis_down()
    advance(a, "s1")
    advance(b, "s1")
    cluster.redis_up(a, b)
    assert a.get("s1")["question_number"] == 3
    assert advance(b, "s1") == 4  # and the lagging Redis copy can be written again
    assert a.get("s1")["question_number"] == 4


def test_stale_writer_is_refused_while_redis_is_down(cluster):
    a, b = cluster.worker(), cluster.worker()
    start(a)
    cluster.redis_down()
    old = a.get("s1")
    advance(b, "s1")
    old["question_number"] = 99
    with pytest.raises(StaleSessionError):
        a.set("s1", old)


def test_stale_writer_is_refused_by_the_checkpoint_when_the_redis_key_is_gone(cluster):
    a, b = cluster.worker(), cluster.worker()
    start(a)
    old = a.get("s1")
    advance(b, "s1")
    advance(b, "s1")
    a._client.delete(f"{REDIS_KEY_PREFIX}s1")  # expired or flushed
    old["question_number"] = 99
    old["store_version"] = a.set("s1", old)
    with pytest.raises(StaleSessionError):
        a.checkpoint("s1", old)
    assert a.get("s1")["question_number"] == 3


def test_no_redis_and_no_database_still_runs(cluster):
    a = cluster.worker(durable=False)
    cluster.redis_down()
    start(a)
    assert advance(a, "s1") == 2


def test_database_outage_keeps_the_interview_going(cluster):
    a = cluster.worker()
    start(a)
    cluster.redis_down()
    state = a.get("s1")
    cluster.durable.down = True
    state["question_number"] = 2
    state["store_version"] = a.set("s1", state)
    a.checkpoint("s1", state)
    assert a.get("s1")["question_number"] == 2
    cluster.durable.down = False
    a.flush()
    assert cluster.durable.load("s1")["question_number"] == 2


def test_redis_that_was_down_is_picked_up_again(cluster):
    cluster.redis_down()
    a = cluster.worker()
    start(a)
    cluster.redis_up(a)
    advance(a, "s1")
    assert cluster.worker().get("s1")["question_number"] == 2


def test_session_key_has_a_ttl(cluster):
    a = cluster.worker()
    start(a)
    assert 0 < a._client.ttl(f"{REDIS_KEY_PREFIX}s1") <= 24 * 3600


def test_state_written_in_the_old_string_format_is_still_read(cluster):
    a = cluster.worker(durable=False)
    a._client.set(f"{REDIS_KEY_PREFIX}old", json.dumps({"session_id": "old", "question_number": 4}))
    assert a.get("old")["question_number"] == 4
    assert advance(a, "old") == 5


def test_pop_removes_both_copies(cluster):
    a = cluster.worker()
    start(a)
    assert a.pop("s1")["question_number"] == 1
    assert a.get("s1") is None
    assert cluster.durable.rows == {}


async def test_engine_turns_alternate_between_workers(
    cluster, stub_llm, fake_evidence_repo, fake_repos
):
    turn = [EVALUATOR_JSON, GOVERNOR_JSON, CONDUCTOR_TURN_JSON]
    stub_llm(responses=[STRATEGY_JSON, "Question: First question?", *turn, *turn, *turn])
    a, b = cluster.worker(), cluster.worker()
    await InterviewEngine(store=a).start_session(make_v4_state(session_id="e1"))

    numbers = [b.get("e1")["question_number"]]
    for store in (b, a, b):
        await InterviewEngine(store=store).process_answer("e1", "I built a queue with retries.")
        numbers.append(a.get("e1")["question_number"])

    assert numbers == sorted(set(numbers)), numbers
    assert len(numbers) == 4
    assert a.get("e1")["store_version"] == 4
    assert cluster.durable.load("e1")["question_number"] == numbers[-1]
