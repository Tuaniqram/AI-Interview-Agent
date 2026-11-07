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


# --- question writing: stronger model by default, longer conversation window ---------------------


async def test_conductor_question_uses_the_strong_tier_by_default(stub_llm, monkeypatch):
    from app.agents.generation.question_generator import _generate_conductor_turn
    from tests.conftest import CONDUCTOR_TURN_JSON

    monkeypatch.delenv("QUESTION_LLM_TIER", raising=False)
    stub = stub_llm(response=CONDUCTOR_TURN_JSON)
    await _generate_conductor_turn(
        state=make_v4_state(), phase="technical", target_competency="tech_core", job_role="Backend Developer",
        difficulty=2, hypothesis_text="", competency_info="", last_answer="",
    )
    assert stub.calls[0]["tier"] == "strong"


async def test_plain_question_uses_the_strong_tier_by_default(stub_llm, monkeypatch):
    from app.agents.generation.question_generator import _generate_llm_question

    monkeypatch.delenv("QUESTION_LLM_TIER", raising=False)
    stub = stub_llm(response="Question: How did you test it?")
    await _generate_llm_question(
        phase="technical", target_competency="tech_core", job_role="Backend Developer", difficulty=2,
        approach="", hypothesis_text="", competency_info="", candidate_profile={}, persona="friendly",
        followup_number=0, question_number=0, total_questions=8, conversation_history=[],
    )
    assert stub.calls[0]["tier"] == "strong"


async def test_question_tier_can_be_switched_back_to_cheap(stub_llm, monkeypatch):
    from app.agents.generation.question_generator import _generate_llm_question

    monkeypatch.setenv("QUESTION_LLM_TIER", "cheap")
    stub = stub_llm(response="Question: How did you test it?")
    await _generate_llm_question(
        phase="technical", target_competency="tech_core", job_role="Backend Developer", difficulty=2,
        approach="", hypothesis_text="", competency_info="", candidate_profile={}, persona="friendly",
        followup_number=0, question_number=0, total_questions=8, conversation_history=[],
    )
    assert stub.calls[0]["tier"] == "cheap"


def test_an_unknown_question_tier_falls_back_to_strong(monkeypatch):
    from app.agents.generation.question_generator import _question_tier

    monkeypatch.setenv("QUESTION_LLM_TIER", "bogus")
    assert _question_tier() == "strong"


def test_question_prompt_sees_the_last_ten_turns_in_full_detail():
    from app.agents.generation.question_generator import HISTORY_CHARS, HISTORY_TURNS, _question_prompt_vars

    history = [{"role": "user" if i % 2 else "assistant", "content": f"turn-{i} " + "x" * 700} for i in range(14)]
    variables = _question_prompt_vars(
        job_role="Dev", target_competency="tech_core", phase="technical", difficulty=1, persona="conductor",
        hypothesis="", competency_info="", approach="", followup_number=0, question_number=0,
        total_questions=8, conversation_history=history, candidate_profile={},
    )
    shown = variables["conversation_history"].splitlines()
    assert len(shown) == HISTORY_TURNS == 10
    assert "turn-4 " in shown[0] and "turn-13 " in shown[-1]
    assert all(len(line) <= HISTORY_CHARS + len("assistant: ") for line in shown)


# --- paid OpenRouter models come first, Groq is the backup ---------------------------------


def _names(chain):
    return [m.model_name for m in chain._models]


def test_strong_chain_is_paid_openrouter_then_groq_then_free_then_local():
    from app.models.llm import _GROQ_STRONG_MODEL, _OPENROUTER_STRONG_MODEL

    assert _names(get_llm("strong")) == [_OPENROUTER_STRONG_MODEL, _GROQ_STRONG_MODEL, "openrouter/free", "one"]


def test_cheap_chain_tries_both_cheap_models_before_the_strong_chain():
    from app.models.llm import _GROQ_CHEAP_MODEL, _OPENROUTER_CHEAP_MODEL

    names = _names(get_llm("cheap"))
    assert names[:2] == [_OPENROUTER_CHEAP_MODEL, _GROQ_CHEAP_MODEL]
    assert names[2:] == _names(get_llm("strong"))


def test_openrouter_models_use_openrouters_reasoning_setting_not_groqs():
    from app.models.llm import OPENROUTER_BASE_URL

    paid = [m for m in get_llm("strong")._models if str(m.openai_api_base) == OPENROUTER_BASE_URL and m.model_name != "openrouter/free"]
    assert len(paid) == 1
    assert paid[0].extra_body == {"reasoning": {"effort": "low"}}


def _providers(chain):
    from app.models.llm import GROQ_BASE_URL, OPENROUTER_BASE_URL

    return [
        {GROQ_BASE_URL: "groq", OPENROUTER_BASE_URL: "openrouter"}.get(str(m.openai_api_base), "local")
        for m in chain._models
    ]


def test_paid_openrouter_is_tried_before_groq_in_both_tiers():
    assert _providers(get_llm("strong")) == ["openrouter", "groq", "openrouter", "local"]
    assert _providers(get_llm("cheap")) == ["openrouter", "groq", "openrouter", "groq", "openrouter", "local"]
    # the model in front of each tier is the paid one, not openrouter/free
    assert get_llm("strong")._models[0].model_name != "openrouter/free"
    assert get_llm("cheap")._models[0].model_name != "openrouter/free"
