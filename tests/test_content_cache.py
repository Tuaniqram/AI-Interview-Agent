"""Caches for work whose input repeats, shared by workers; and the startup recovery done once."""
import asyncio
import uuid
from types import SimpleNamespace

import fakeredis
import pytest
from fakeredis import FakeAsyncRedis

from app.intelligence import company_cache
from app.marketplace import fit_evaluation as fe
from app.engine.session_lock import DistributedSessionLocks
from app.services import content_cache
from app.services.redis_client import AsyncLink


@pytest.fixture
def server(monkeypatch):
    server = fakeredis.FakeServer()
    monkeypatch.setattr(content_cache, "_link",
                        AsyncLink("t", FakeAsyncRedis(server=server, decode_responses=True)))
    monkeypatch.setattr(content_cache, "_sync_client",
                        fakeredis.FakeStrictRedis(server=server, decode_responses=True))
    monkeypatch.setattr("app.services.llm_service.get_llm_service",
                        lambda: SimpleNamespace(_cache_enabled=True))
    return server


def redis(server):
    return fakeredis.FakeStrictRedis(server=server, decode_responses=True)


async def test_same_cv_is_parsed_once(server, monkeypatch):
    from app.candidates import resume_service

    calls = []

    class Model:
        async def ainvoke(self, messages):
            calls.append(1)
            return SimpleNamespace(content='{"skills": ["python"]}')

    monkeypatch.setattr(resume_service, "llm", Model())
    text = "Jane Doe, Python developer"
    assert await resume_service.parse_resume(text) == {"skills": ["python"], "years_of_experience": None}
    assert await resume_service.parse_resume(text) == {"skills": ["python"], "years_of_experience": None}
    assert len(calls) == 1
    (key,) = redis(server).keys("aura:cache:*")
    assert "Jane" not in key and 0 < redis(server).ttl(key) <= 24 * 3600


async def test_a_failed_parse_is_not_cached(server, monkeypatch):
    from app.candidates import resume_service

    class Broken:
        async def ainvoke(self, messages):
            raise RuntimeError("provider down")

    monkeypatch.setattr(resume_service, "llm", Broken())
    assert (await resume_service.parse_resume("cv"))["skills"] == []
    assert redis(server).keys("aura:cache:*") == []


async def test_same_cv_against_same_listing_is_evaluated_once_unless_rerun(server, monkeypatch):
    calls = []

    async def fake_llm(prompt):
        calls.append(prompt)
        return {"fit_score": 6 + len(calls), "fit_summary": "ok"}

    monkeypatch.setattr(fe, "_call_llm", fake_llm)
    first = await fe._evaluate_prompt("cv A + listing", set(), fresh=False)
    again = await fe._evaluate_prompt("cv A + listing", set(), fresh=False)
    assert (first.fit_score, again.fit_score, len(calls)) == (7, 7, 1)
    rerun = await fe._evaluate_prompt("cv A + listing", set(), fresh=True)
    assert (rerun.fit_score, len(calls)) == (8, 2)
    assert (await fe._evaluate_prompt("cv A + listing", set(), fresh=False)).fit_score == 8
    await fe._evaluate_prompt("cv B + listing", set(), fresh=False)
    assert len(calls) == 3


async def test_role_profile_is_shared_between_workers(server, monkeypatch):
    from app.intelligence import role_competency_profiler as profiler

    calls = []
    entries = [{"id": f"tech_{i}", "name": f"Skill {i}", "category": "technical", "weight": 1.0} for i in range(4)]

    async def fake_parse(*args, **kwargs):
        calls.append(1)
        return {}

    monkeypatch.setattr("app.intelligence._helpers.parse_llm_json_with_retry", fake_parse)
    monkeypatch.setattr(profiler, "_validate_suggestions", lambda data: (entries, "because"))
    context = profiler.build_role_context(job_role="Backend Developer")
    profiler._SUGGESTION_CACHE.clear()
    got, source, _ = await profiler.suggest_competencies(context)
    profiler._SUGGESTION_CACHE.clear()  # another worker: nothing in its memory
    again, source_again, _ = await profiler.suggest_competencies(context)
    profiler._SUGGESTION_CACHE.clear()
    assert (source, source_again) == ("ai:llm", "cache:shared") and got == again and len(calls) == 1


def test_unchanged_documents_are_not_embedded_again(server):
    from app.rag.pinecone_store import CachedEmbeddings

    embedded = []

    class Inner:
        def embed_documents(self, texts):
            embedded.extend(texts)
            return [[float(len(t)), 0.5] for t in texts]

    cached = CachedEmbeddings(Inner())
    first = cached.embed_documents(["alpha", "beta"])
    second = cached.embed_documents(["alpha", "beta", "gamma!"])
    assert second[:2] == first and second[2] == [6.0, 0.5]
    assert embedded == ["alpha", "beta", "gamma!"]
    assert all(0 < redis(server).ttl(k) <= 7 * 24 * 3600 for k in redis(server).keys("aura:cache:*"))


async def test_cache_switch_off_and_redis_down_mean_a_miss(server, monkeypatch):
    key = content_cache.key("t", "x")
    await content_cache.put(key, 1, 60)
    assert await content_cache.get(key) == 1
    monkeypatch.setattr("app.services.llm_service.get_llm_service",
                        lambda: SimpleNamespace(_cache_enabled=False))  # the simulator's switch
    assert await content_cache.get(key) is None
    monkeypatch.setattr("app.services.llm_service.get_llm_service",
                        lambda: SimpleNamespace(_cache_enabled=True))
    server.connected = False
    assert await content_cache.get(key) is None
    await content_cache.put(key, 2, 60)  # must not raise


async def test_new_documents_invalidate_the_company_brain_on_every_worker(server, monkeypatch):
    built = []

    async def builder(**kwargs):
        built.append(1)
        return {"rag_metadata": {"success": True}, "build": len(built)}

    monkeypatch.setattr(company_cache, "create_sync_client",
                        lambda: fakeredis.FakeStrictRedis(server=server, decode_responses=True))
    monkeypatch.setattr(company_cache, "_link",
                        AsyncLink("t", FakeAsyncRedis(server=server, decode_responses=True)))
    company_cache._cache.clear()

    async def get():
        company_cache._cache.clear()  # each call is a worker with its own memory
        return (await company_cache.get_or_build_company_brain(org_id="A", job_role="x", builder=builder))["build"]

    assert [await get(), await get()] == [1, 1]
    company_cache.invalidate_company_brain(org_id="A")  # handled by one worker
    assert [await get(), await get()] == [2, 2]
    company_cache._cache.clear()


async def test_two_workers_resuming_evaluate_an_application_once(server, monkeypatch):
    app_id = uuid.uuid4()
    row = SimpleNamespace(fit_status="pending")
    runs = []

    class Db:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, model, key):
            return row

    async def fake_evaluate(application_id, db, fresh=False):
        runs.append(application_id)
        await asyncio.sleep(0.05)
        row.fit_status = "completed"

    monkeypatch.setattr("app.database.session.get_session_factory", lambda: (lambda: Db()))
    monkeypatch.setattr(fe, "evaluate_application_fit", fake_evaluate)

    async def worker():
        monkeypatch.setattr(fe, "_evaluation_locks", DistributedSessionLocks(
            ttl_s=60, client=FakeAsyncRedis(server=server, decode_responses=True)))
        await fe.run_application_fit_evaluation(str(app_id))

    await asyncio.gather(worker(), worker())
    await worker()  # a worker that starts later
    assert len(runs) == 1


async def test_llm_replies_are_not_cached_by_prompt(monkeypatch):
    from app.services.llm_service import LLMService

    calls = []

    class Model:
        async def ainvoke(self, messages, config=None, **kwargs):
            calls.append(1)
            return SimpleNamespace(content=f"reply {len(calls)}")

    monkeypatch.setattr("app.services.llm_service.llm", Model())
    service = LLMService()
    assert [await service.invoke("same prompt"), await service.invoke("same prompt")] == ["reply 1", "reply 2"]
