"""V5 engine flow routing — the ``v5_*`` flow types run the V5 pipeline
(conditional-LLM governor before question generation + opt-in snapshot
persistence); the ``v4_evidence_driven`` flow keeps the V4 pipeline and never
touches the V5 persister."""
import pytest

from app.engine.engine import InterviewEngine, _V5_FLOW_TYPES
from app.services.v4_session_store import MemoryV4SessionStore
from tests.conftest import (
    CONDUCTOR_TURN_JSON,
    EVALUATOR_JSON,
    GOVERNOR_JSON,
    STRATEGY_JSON,
    make_v4_state,
)


class FakeV5Persister:
    def __init__(self):
        self.snapshots = []

    async def save_snapshot(self, brain):
        self.snapshots.append(brain)


def _answer_llm_responses():
    return [
        EVALUATOR_JSON,
        GOVERNOR_JSON,
        CONDUCTOR_TURN_JSON,
    ]


@pytest.fixture
def fake_store(tmp_path):
    return MemoryV4SessionStore(db_path=str(tmp_path / "sessions.json"))


@pytest.mark.parametrize("flow_type", sorted(_V5_FLOW_TYPES))
async def test_v5_flows_route_to_v5_pipeline(
    flow_type, fake_store, stub_llm, fake_evidence_repo, fake_repos
):
    stub_llm(
        responses=[
            STRATEGY_JSON,
            "Question: First question?",
            *_answer_llm_responses(),
        ]
    )
    persister = FakeV5Persister()
    engine = InterviewEngine(store=fake_store, v5_persister=persister)
    session_id = f"v5-{flow_type}"
    state = make_v4_state(session_id=session_id, flow_type=flow_type)

    await engine.start_session(state)
    response = await engine.process_answer(session_id, "I built distributed systems.")

    assert response["status"] == "in_progress"
    assert response["next_question"]["text"]
    assert persister.snapshots, "v5 persister should be called for v5 flows"
    assert persister.snapshots[-1].session_id == session_id

    saved = fake_store.get(session_id)
    assert saved["difficulty_profile"] is not None
    assert saved["difficulty_profile"]["level"] >= 1


async def test_all_flows_share_the_v5_pipeline(fake_store, stub_llm, fake_evidence_repo, fake_repos):
    """The v4_evidence_driven flow runs the same pipeline as v5 flows — the
    conditional difficulty governor + snapshot persistence are no longer gated
    on the flow_type."""
    stub_llm(
        responses=[
            STRATEGY_JSON,
            "Question: First question?",
            *_answer_llm_responses(),
        ]
    )
    persister = FakeV5Persister()
    engine = InterviewEngine(store=fake_store, v5_persister=persister)
    session_id = "v4-flow"
    state = make_v4_state(session_id=session_id, flow_type="v4_evidence_driven")

    await engine.start_session(state)
    response = await engine.process_answer(session_id, "I built distributed systems.")

    assert response["status"] == "in_progress"
    assert persister.snapshots, "unified pipeline persists snapshots for every flow"
    assert fake_store.get(session_id)["difficulty_profile"] is not None


async def test_v5_flow_persister_failures_are_nonfatal(
    fake_store, stub_llm, fake_evidence_repo, fake_repos
):
    stub_llm(
        responses=[
            STRATEGY_JSON,
            "Question: First question?",
            *_answer_llm_responses(),
        ]
    )

    class BrokenPersister:
        async def save_snapshot(self, brain):
            raise RuntimeError("db down")

    engine = InterviewEngine(store=fake_store, v5_persister=BrokenPersister())
    session_id = "v5-broken"
    state = make_v4_state(session_id=session_id, flow_type="v5_evidence_driven")

    await engine.start_session(state)
    response = await engine.process_answer(session_id, "I built distributed systems.")

    assert response["status"] == "in_progress"


async def test_engine_without_persister_is_quiet(fake_store, stub_llm, fake_evidence_repo, fake_repos):
    stub_llm(
        responses=[
            STRATEGY_JSON,
            "Question: First question?",
            *_answer_llm_responses(),
        ]
    )
    engine = InterviewEngine(store=fake_store)
    session_id = "v5-no-persister"
    state = make_v4_state(session_id=session_id, flow_type="v5_company_context")

    await engine.start_session(state)
    response = await engine.process_answer(session_id, "I built distributed systems.")

    assert response["status"] == "in_progress"


async def test_v5_company_context_flow_injects_company_brain_into_questions(
    fake_store, stub_llm, fake_evidence_repo, fake_repos
):
    stub = stub_llm(
        responses=[
            STRATEGY_JSON,
            "Question: First question?",
            *_answer_llm_responses(),
        ]
    )
    engine = InterviewEngine(store=fake_store)
    session_id = "v5-company-context"
    state = make_v4_state(
        session_id=session_id,
        flow_type="v5_company_context",
        company_brain={
            "company_vision": "Build the fastest fintech rails in the world.",
            "technical_stack": ["python", "kubernetes", "postgresql"],
            "culture": ["ownership", "transparency"],
        },
    )

    await engine.start_session(state)
    await engine.process_answer(session_id, "I built distributed systems.")

    question_prompts = [
        c["prompt"] for c in stub.calls if "Target Competency" in c["prompt"]
    ]
    assert question_prompts
    first = question_prompts[0]
    assert "Company Context" in first
    assert "python" in first
    assert "fastest fintech rails" in first
