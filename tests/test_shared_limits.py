"""Rate limits and LLM budgets counted across workers. Each object below stands for one worker."""
from types import SimpleNamespace

import fakeredis
import pytest
from fakeredis import FakeAsyncRedis
from httpx import ASGITransport, AsyncClient
from starlette.responses import PlainTextResponse

from app.engine.engine import InterviewEngine
from app.exceptions import LLMBudgetExceeded
from app.middleware.rate_limit import RateLimitMiddleware
from app.services import llm_budget
from app.services.llm_service import LLMService
from app.services.v4_session_store import MemoryV4SessionStore
from tests.conftest import CONDUCTOR_TURN_JSON, make_v4_state


@pytest.fixture
def server():
    return fakeredis.FakeServer()


def client_for(server):
    return FakeAsyncRedis(server=server, decode_responses=True)


async def _ok(scope, receive, send):
    await PlainTextResponse("ok")(scope, receive, send)


def limiter(server, limit):
    return RateLimitMiddleware(_ok, max_requests=limit, window_seconds=60, redis_client=client_for(server))


async def statuses(apps, n, ip="1.2.3.4"):
    """``n`` requests from one address, dealt round-robin to the workers."""
    out = []
    for i in range(n):
        transport = ASGITransport(app=apps[i % len(apps)], client=(ip, 1))
        async with AsyncClient(transport=transport, base_url="http://t") as http:
            out.append((await http.get("/api/v1/x")).status_code)
    return out


@pytest.mark.parametrize("limit", [20, 120])
async def test_the_limit_holds_across_two_workers(server, limit):
    workers = [limiter(server, limit), limiter(server, limit)]
    got = await statuses(workers, limit + 10)
    assert got.count(200) == limit and got.count(429) == 10
    assert (await statuses(workers, 1, ip="5.6.7.8")) == [200]  # another address has its own bucket


async def test_auth_and_general_limits_count_separately_and_keys_expire(server):
    await statuses([limiter(server, 20)], 20)
    assert await statuses([limiter(server, 120)], 1) == [200]
    redis = client_for(server)
    keys = await redis.keys("aura:rl:*")
    assert len(keys) == 2 and not any("1.2.3.4" in k for k in keys)
    for key in keys:
        assert 0 < await redis.pttl(key) <= 60_000


async def test_rate_limit_falls_back_to_memory_when_redis_is_down(server):
    server.connected = False
    worker = limiter(server, 5)
    assert await statuses([worker], 7) == [200] * 5 + [429] * 2


# ── LLM budget ───────────────────────────────────────────────────────────


@pytest.fixture
def budget(server, monkeypatch):
    monkeypatch.setenv("LLM_BUDGET_SESSION_CALLS", "5")
    monkeypatch.setenv("LLM_BUDGET_ORG_DAILY_CALLS", "8")
    monkeypatch.setattr(llm_budget, "_budget", llm_budget.Budget(client_for(server)))


async def test_session_cap_is_shared_between_workers(server, budget):
    a, b = llm_budget.Budget(client_for(server)), llm_budget.Budget(client_for(server))
    got = [await (a, b)[i % 2].take("s1", None) for i in range(7)]
    assert got == [0] * 5 + [1, 1]
    assert 0 < await client_for(server).ttl("aura:llm:budget:session:s1") <= 24 * 3600


async def test_organization_daily_cap(budget):
    b = llm_budget._budget
    first = [await b.take("s1", "org") for _ in range(5)]
    second = [await b.take("s2", "org") for _ in range(4)]
    assert first == [0] * 5 and second == [0, 0, 0, 2]
    assert await b.take("s3", None) == 0  # no organization: only the interview cap


async def test_budget_still_counts_when_redis_is_down(server, budget):
    server.connected = False
    got = [await llm_budget._budget.take("s1", None) for _ in range(6)]
    assert got == [0] * 5 + [1]


@pytest.fixture
def counting_llm(monkeypatch):
    calls = []

    class Model:
        async def ainvoke(self, messages, config=None, **kwargs):
            calls.append(messages)
            return SimpleNamespace(content=CONDUCTOR_TURN_JSON)

    service = LLMService()
    service._cache_enabled = False
    monkeypatch.setattr("app.services.llm_service.llm", Model())
    monkeypatch.setattr("app.services.llm_service.get_llm", lambda tier=None: Model())
    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: service)
    return SimpleNamespace(calls=calls, service=service)


async def test_service_stops_calling_the_model_over_the_cap(budget, counting_llm):
    with llm_budget.scope("s1") as scope:
        for _ in range(5):
            await counting_llm.service.invoke("hello")
        with pytest.raises(LLMBudgetExceeded):
            await counting_llm.service.invoke("hello")
        assert scope.exceeded
    assert len(counting_llm.calls) == 5
    await counting_llm.service.invoke("outside any interview")
    assert len(counting_llm.calls) == 6


async def test_interview_over_its_budget_finishes_and_is_flagged(
    budget, counting_llm, tmp_path, fake_evidence_repo, fake_repos
):
    store = MemoryV4SessionStore(db_path=str(tmp_path / "s.json"))
    engine = InterviewEngine(store=store)
    await engine.start_session(make_v4_state(session_id="s1", max_questions=3))
    for _ in range(6):
        response = await engine.process_answer("s1", "I used idempotency keys and a retry queue.")
        if response.get("interview_complete"):
            break

    assert response["interview_complete"], response
    assert len(counting_llm.calls) == 5  # nothing after the cap
    state = store.get("s1")
    assert state["llm_budget_exceeded"] is True
    decision = state["hiring_decision"]
    assert decision["flag_review"] is True
    assert "llm_budget" in [a["rule"] for a in decision["adjustments"]]
