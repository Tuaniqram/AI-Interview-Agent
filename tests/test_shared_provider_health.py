"""What one worker learns about a failing provider, every worker knows.

Each ``chain()`` below stands for one worker's client object: same Redis, separate memory.
"""
from types import SimpleNamespace

import fakeredis
import pytest
from fakeredis import FakeAsyncRedis

from app.models.llm import FallbackLLM, GROQ_BASE_URL, OPENROUTER_BASE_URL
from app.models.provider_health import ProviderHealth
from app.services.redis_client import AsyncLink


class ApiError(Exception):
    def __init__(self, status):
        super().__init__(f"Error code: {status}")
        self.status_code = status


class Model:
    def __init__(self, name, base, log, fail):
        self.model_name, self.openai_api_base, self.log, self.fail = name, base, log, fail

    async def ainvoke(self, messages, config=None, **kwargs):
        self.log.append(self.model_name)
        if self.fail.get(self.model_name):
            raise ApiError(self.fail[self.model_name])
        return SimpleNamespace(content="ok", usage_metadata={"total_tokens": 900})


class World:
    """The providers as they currently behave, one Redis, one wall clock."""

    def __init__(self):
        self.server = fakeredis.FakeServer()
        self.fail: dict[str, int] = {}
        self.time = 1_000_000.0
        self.log: list[str] = []

    def chain(self, *names):
        models = [
            Model(n, GROQ_BASE_URL if n.startswith("groq") else OPENROUTER_BASE_URL, self.log, self.fail)
            for n in (names or ("or-120b", "groq-120b"))
        ]
        health = ProviderHealth(
            link=AsyncLink("test", FakeAsyncRedis(server=self.server, decode_responses=True)),
            clock=lambda: self.time, now=lambda: self.time,
        )
        return FallbackLLM(models, health=health)

    def redis(self):
        return FakeAsyncRedis(server=self.server, decode_responses=True)

    async def call(self, chain) -> list[str]:
        self.log.clear()
        await chain.ainvoke([])
        return list(self.log)


@pytest.fixture
def world():
    return World()


@pytest.mark.parametrize("status", [402, 429])
async def test_a_provider_tripped_by_one_worker_is_skipped_by_another(world, status):
    a, b = world.chain(), world.chain()
    world.fail["or-120b"] = status
    assert await world.call(a) == ["or-120b", "groq-120b"]
    assert await world.call(b) == ["groq-120b"]


async def test_account_errors_block_every_paid_model_of_the_provider(world):
    a, b = world.chain(), world.chain("or-20b", "openrouter/free", "groq-20b")
    world.fail["or-120b"] = 402
    await world.call(a)
    assert await world.call(b) == ["openrouter/free"]  # free models need no balance


async def test_a_model_error_blocks_only_that_model(world):
    a, b = world.chain(), world.chain("or-20b", "groq-20b")
    world.fail["or-120b"] = 404
    await world.call(a)
    assert await world.call(b) == ["or-20b"]


async def test_after_the_cooldown_one_caller_probes_and_a_success_closes_it(world):
    a, b = world.chain(), world.chain()
    world.fail["or-120b"] = 402
    await world.call(a)
    world.time += 15 * 60 + 1
    health = b._health
    blocked, half_open = await health.inspect(b._models)
    assert blocked == [0, 0] and half_open == [True, False]
    assert await health.claim_probe(b._models[0]) is True
    assert await world.call(a) == ["groq-120b"]  # b holds the probe
    await health.succeeded(b._models[0], was_suspect=True)
    world.fail.clear()
    assert await world.call(a) == ["or-120b"]
    assert await world.call(b) == ["or-120b"]


async def test_an_ordinary_success_does_not_close_a_breaker(world):
    a, b = world.chain(), world.chain()
    world.fail["or-120b"] = 402
    await world.call(a)
    await b._health.succeeded(b._models[0])  # a request sent before the balance ran out
    assert await world.call(b) == ["groq-120b"]


async def test_groq_daily_tokens_are_counted_across_workers(world, monkeypatch):
    monkeypatch.setenv("GROQ_DAILY_TOKEN_LIMIT", "1800")
    a, b = world.chain("groq-120b", "or-120b"), world.chain("groq-120b", "or-120b")
    assert await world.call(a) == ["groq-120b"]
    assert await world.call(b) == ["groq-120b"]
    assert await world.call(a) == ["or-120b"]  # 2 x 900 tokens used


async def test_error_counts_and_ttls(world):
    a = world.chain()
    world.fail["or-120b"] = 429
    await world.call(a)
    redis = world.redis()
    assert await redis.get("aura:llm:errors:openrouter:429") == "1"
    for key in await redis.keys("aura:llm:*"):
        assert await redis.ttl(key) > 0, key


async def test_redis_down_keeps_a_local_breaker(world):
    world.server.connected = False
    a = world.chain()
    world.fail["or-120b"] = 402
    assert await world.call(a) == ["or-120b", "groq-120b"]
    assert await world.call(a) == ["groq-120b"]
