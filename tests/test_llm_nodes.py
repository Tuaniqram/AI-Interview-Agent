"""LLM-backed v4 nodes with a stubbed get_llm_service: question generation,
unified evaluation, and synthesis — including fallback paths."""
import json

from app.agents.generation.question_generator import question_generator_node
from app.agents.evaluation.synthesis import synthesis_node
from app.agents.evaluation.candidate_evaluator import unified_evaluator_node
from tests.conftest import EVALUATOR_JSON, SYNTHESIS_JSON, make_v4_state


async def test_question_generator_uses_llm_and_strips_prefix(stub_llm):
    stub = stub_llm(response="Question: What was your hardest bug?")
    state = await question_generator_node(make_v4_state(question_number=0))
    assert state["current_question"] == "What was your hardest bug?"
    assert state["question_number"] == 1
    assert len(state["questions_asked"]) == 1
    assert state["questions_asked"][0]["text"] == "What was your hardest bug?"
    assert stub.calls[0]["temperature"] == 0.8


async def test_question_generator_falls_back_when_llm_fails(stub_llm):
    stub_llm(fail=True)
    state = await question_generator_node(make_v4_state())
    assert state["current_question"]
    assert "Question:" not in state["current_question"]
    assert state["question_number"] == 1


async def test_question_generator_falls_back_on_empty_response(stub_llm):
    stub_llm(response="")
    state = await question_generator_node(make_v4_state())
    assert state["current_question"]


async def test_unified_evaluator_parses_six_dimensions(stub_llm):
    stub = stub_llm(response=json.dumps(EVALUATOR_JSON))
    state = await unified_evaluator_node(make_v4_state(
        current_question="Q",
        candidate_answer="A",
        question_objective={"target_competency": "tech_core"},
    ))
    assert set(state["unified_evaluation"].keys()) == {
        "technical", "communication", "reasoning", "behavioral", "confidence", "completeness",
    }
    assert state["unified_evaluation"]["behavioral"]["score"] is None
    assert state["evaluation_score"] == 7.6
    assert stub.calls[0]["max_tokens"] == 1500


async def test_unified_evaluator_empty_answer_skips_llm(stub_llm):
    stub = stub_llm(response=json.dumps(EVALUATOR_JSON))
    state = await unified_evaluator_node(make_v4_state(candidate_answer="   "))
    assert not stub.calls
    assert state["evaluation_score"] is None


async def test_synthesis_builds_final_report(stub_llm):
    stub_llm(response=SYNTHESIS_JSON)
    state = await synthesis_node(make_v4_state(job_role="Backend Engineer"))
    report = state["final_report"]
    # The LLM's holistic_score (7.4) must NOT win — the canonical composite
    # anchors the report, the LLM only narrates.
    assert report["holistic_score"] != 7.4
    assert report["holistic_score"] == report["average_score"]
    assert report["fit_assessment"] == "Good Fit"
    assert "Communicates clearly" in report["key_strengths"]


async def test_synthesis_uses_fallback_on_llm_failure(stub_llm):
    stub_llm(fail=True)
    state = await synthesis_node(make_v4_state(job_role="Backend Engineer"))
    assert state["final_report"]["fit_assessment"] == "Potential Fit"
    assert state["final_report"]["holistic_score"] is not None


async def test_synthesis_uses_fallback_on_invalid_json(stub_llm):
    stub_llm(response="this is not json")
    state = await synthesis_node(make_v4_state(job_role="Backend Engineer"))
    assert state["final_report"]["fit_assessment"] == "Potential Fit"
