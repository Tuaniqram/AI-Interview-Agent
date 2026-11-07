"""LLM tiering: cheap tier for extraction/formatting/classification, strong
tier for reasoning/decisions, and tier-aware cache keys."""
import json

from tests.conftest import EVALUATOR_JSON, SYNTHESIS_JSON, make_v4_state

from app.agents.decision.hiring_decision import hiring_decision_node
from app.agents.evaluation.candidate_evaluator import unified_evaluator_node
from app.agents.evaluation.synthesis import synthesis_node
from app.models.llm import get_llm
from app.services import llm_service as llm_service_module

DECISION_JSON = (
    '{"decision": "undecided", "confidence": 0.6, "rationale": "mixed evidence", '
    '"next_steps": ["schedule a short probe round"]}'
)


def test_tiers_resolve_to_distinct_chains():
    cheap = get_llm("cheap")
    strong = get_llm("strong")
    assert cheap.model_name != strong.model_name
    from app.models.llm import _GROQ_CHEAP_MODEL, _GROQ_STRONG_MODEL

    assert cheap.model_name.startswith(_GROQ_CHEAP_MODEL)
    assert strong.model_name.startswith(_GROQ_STRONG_MODEL)
    assert _GROQ_CHEAP_MODEL != _GROQ_STRONG_MODEL


async def test_invoke_passes_tier_through(stub_llm):
    stub = stub_llm(response="hello")
    service = llm_service_module.get_llm_service()
    await service.invoke(prompt="hi", tier="cheap")
    assert stub.calls[0]["tier"] == "cheap"


def test_cache_key_differs_by_tier():
    service = llm_service_module.get_llm_service()
    k_strong = service._generate_cache_key("p", 0.3, None, "strong")
    k_cheap = service._generate_cache_key("p", 0.3, None, "cheap")
    k_none = service._generate_cache_key("p", 0.3, None, None)
    assert k_strong != k_cheap
    assert k_none == k_strong


async def test_evaluator_routes_to_cheap_tier(stub_llm):
    stub = stub_llm(response=json.dumps(EVALUATOR_JSON))
    state = make_v4_state(
        current_question="Q",
        candidate_answer="A",
        question_objective={"target_competency": "tech_core"},
    )
    await unified_evaluator_node(state)
    assert stub.calls[0]["tier"] == "cheap"


async def test_synthesis_routes_to_strong_tier(stub_llm):
    stub = stub_llm(response=SYNTHESIS_JSON)
    await synthesis_node(make_v4_state(job_role="Software Engineer"))
    assert stub.calls[0]["tier"] == "strong"


async def test_hiring_decision_routes_to_strong_tier(stub_llm):
    stub = stub_llm(response=DECISION_JSON)
    state = make_v4_state(
        job_role="Backend Engineer",
        final_report={"holistic_score": 7.2, "fit_assessment": "Good Fit"},
        hiring_recommendation={"verdict": "hire", "confidence": 0.8, "coverage_ratio": 0.9},
    )
    await hiring_decision_node(state)
    assert stub.calls[0]["tier"] == "strong"
