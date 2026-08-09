"""Regression tests for the engine response builders (app/engine/builders.py).

Covers the AttributeError fixed in _build_answer_response: when every
hypothesis is refuted, next_target() returns None, so hypothesis_target
becomes None and the response builder must not crash.
"""
from app.agents.planning.competency_planner import competency_planner_node
from app.agents.reasoning.evidence_engine import evidence_extractor_node
from app.agents.reasoning.hypothesis_engine import hypothesis_node
from app.agents.generation.question_generator import question_generator_node
from app.agents.reasoning.reflection_engine import reflection_engine
from app.agents.evaluation.candidate_evaluator import unified_evaluator_node
from app.engine.builders import _build_answer_response, _build_start_response
from app.agents.planning.action_router import route_after_planner
from tests.conftest import ZERO_EVAL_JSON, make_v4_state, refutable_hypotheses


def test_build_answer_response_with_null_hypothesis_target():
    state = make_v4_state(
        hypothesis_target=None,
        next_competency=None,
        evaluation_score=6.5,
        unified_evaluation={"technical": {"score": 8.0, "evidence": "e", "confidence": 0.9, "strengths": [], "weaknesses": []}},
        competency_summary={"tech_core": {"evidence_count": 12, "average_score": 6.5, "gap": 1.0}},
    )
    result = _build_answer_response("s1", state)
    assert result["next_question"]["target_competency"] == ""
    assert result["status"] == "in_progress"


def test_build_start_response_with_null_hypothesis_target():
    state = make_v4_state(hypothesis_target=None, next_competency=None)
    result = _build_start_response("s1", state)
    assert result["hypothesis_target"] is None
    assert result["question"]["target_competency"] == ""


async def test_answer_flow_all_hypotheses_refuted_does_not_crash(
    stub_llm, fake_evidence_repo
):
    """Reproduces the live 500: change_competency action with every hypothesis
    refuted -> hypothesis_target becomes None -> _build_answer_response must
    handle it (the fix)."""
    stub_llm(responses=[ZERO_EVAL_JSON, "Question: Next generic question?"])

    state = make_v4_state(
        question_number=3,
        current_question="System design question?",
        candidate_answer="I design systems with caches and load balancers.",
        question_objective={"target_competency": "tech_core", "question_id": "q3"},
        hypotheses=refutable_hypotheses(),
        hypothesis_target=refutable_hypotheses(1)[0],
        contradictions=[
            {"id": "c1", "severity": "medium"},
            {"id": "c2", "severity": "medium"},
        ],
    )

    state = await unified_evaluator_node(state)
    state = await evidence_extractor_node(state)
    state = await reflection_engine(state)

    action = state.get("reflection_action", "probe")
    if action == "change_competency":
        state = await competency_planner_node(state)
        routed = route_after_planner(state)
        if routed == "finish":
            raise AssertionError("expected question_subgraph, got finish")
        state = await hypothesis_node(state)
    elif action == "finish":
        raise AssertionError("expected change_competency, got finish")

    state = await hypothesis_node(state)
    state = await question_generator_node(state)

    # Saturation (AURA V5): all hypotheses settled -> planner rotates -> the
    # node seeds a fresh untested hypothesis for the planned competency, so the
    # interview keeps probing instead of emitting target-less generic questions.
    assert state["hypothesis_target"] is not None
    assert state["hypothesis_target"]["competency"] == state["next_competency"]["id"]
    assert state["hypothesis_target"]["status"] in ("untested", "testing")
    assert any(h["status"] in ("untested", "testing") for h in state["hypotheses"])

    result = _build_answer_response("s1", state)
    assert result["status"] == "in_progress"
    assert result["next_question"]["target_competency"] == state["next_competency"]["id"]


def test_build_answer_response_recommendation_matches_current_hypotheses():
    """Fix 11: the payload's hiring_recommendation is recomputed from the
    post-update hypotheses so it agrees with hypothesis_progress in the same
    payload (previously the reflection computed it one answer behind)."""
    state = make_v4_state(
        question_number=6,
        competency_summary={
            "tech_core": {"evidence_count": 2, "average_score": 8.0, "gap": 0.0},
            "tech_db": {"evidence_count": 2, "average_score": 7.5, "gap": 0.0},
        },
        hypotheses=[
            {"competency": "tech_core", "status": "confirmed"},
            {"competency": "tech_db", "status": "refuted"},
        ],
        hiring_recommendation={},  # stale/empty on purpose
    )
    result = _build_answer_response("s1", state)
    rec = result["hiring_recommendation"]
    assert rec["confirmed_hypotheses"] == 1
    assert rec["refuted_hypotheses"] == 1
    assert result["hypothesis_progress"]["statuses"] == {"confirmed": 1, "refuted": 1}
    assert rec["confirmed_hypotheses"] + rec["refuted_hypotheses"] == (
        result["hypothesis_progress"]["statuses"]["confirmed"]
        + result["hypothesis_progress"]["statuses"]["refuted"]
    )
