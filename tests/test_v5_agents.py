"""V5 agent upgrades — Bayesian hypothesis probability, 6-dimension difficulty
profile with conditional LLM skip, and the evidence graph edges. All offline."""
import pytest

from app.agents.planning.difficulty_engine import (
    build_difficulty_profile,
    difficulty_governor,
    should_skip_llm_governor,
)
from app.agents.reasoning.evidence_engine import (
    update_evidence_graph,
    evidence_extractor_node,
)
from app.agents.reasoning.hypothesis_engine import (
    PRIOR_CONFIDENCE,
    bayesian_update,
    update_hypotheses,
)
from app.engine.builders import build_report_response
from app.core.interview_state import InterviewState
from tests.conftest import EVALUATOR_JSON, make_v4_state, refutable_hypotheses


def _hypothesis(**overrides) -> dict:
    base = {
        "id": "h1",
        "competency": "tech_core",
        "statement": "Candidate has strong tech_core skills",
        "direction": "positive",
        "confidence": PRIOR_CONFIDENCE,
        "probability": PRIOR_CONFIDENCE,
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "status": "untested",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Bayesian hypothesis updates
# ---------------------------------------------------------------------------

def test_bayesian_update_moves_probability_and_mirrors_confidence():
    h = _hypothesis()
    updated = bayesian_update(
        h,
        {"id": "e1", "competency": "tech_core", "dimension": "technical",
         "score": 7.0, "confidence": 0.9, "evidence_text": "Decent tech_core answer"},
    )
    assert updated["probability"] > PRIOR_CONFIDENCE
    assert updated["confidence"] == updated["probability"]
    assert updated["status"] == "testing"
    assert "e1" in updated["supporting_evidence"]


def test_bayesian_update_contradicts_negative_evidence():
    h = _hypothesis()
    updated = bayesian_update(
        h,
        {"id": "e1", "competency": "tech_core", "dimension": "technical",
         "score": 2.0, "confidence": 0.9, "evidence_text": "Weak tech_core answer"},
    )
    assert updated["probability"] < PRIOR_CONFIDENCE
    assert "e1" in updated["contradicting_evidence"]


def test_update_hypotheses_writes_probability_alongside_confidence():
    h = _hypothesis()
    updated = update_hypotheses(
        [h],
        [{"id": "e1", "competency": "tech_core", "dimension": "technical",
          "score": 8.5, "confidence": 0.9, "evidence_text": "Strong tech_core answer"}],
    )
    assert updated[0]["probability"] > PRIOR_CONFIDENCE
    assert updated[0]["confidence"] > PRIOR_CONFIDENCE


def test_bayesian_never_fully_certain_on_single_evidence():
    h = _hypothesis()
    updated = bayesian_update(
        h,
        {"id": "e1", "competency": "tech_core", "dimension": "technical",
         "score": 10.0, "confidence": 1.0, "evidence_text": "perfect answer"},
    )
    assert 0.0 < updated["probability"] < 1.0


# ---------------------------------------------------------------------------
# Difficulty profile + conditional LLM skip
# ---------------------------------------------------------------------------

def test_difficulty_profile_has_six_dimensions():
    profile = build_difficulty_profile(
        {"difficulty_level": 2}, delta=0, rationale="steady"
    )
    assert profile["level"] == 2
    assert len(profile["dimensions"]) == 6
    assert {d["name"] for d in profile["dimensions"]} == {
        "problem_complexity", "abstraction_depth", "time_pressure",
        "scaffolding_needed", "precision_required", "follow_up_aggression",
    }


def test_difficulty_profile_adapts_to_delta():
    up = build_difficulty_profile({"difficulty_level": 2}, delta=1, rationale="strong")
    down = build_difficulty_profile({"difficulty_level": 2}, delta=-1, rationale="weak")
    assert up["abstraction_depth"] > down["abstraction_depth"]
    assert up["scaffolding_needed"] < down["scaffolding_needed"]
    assert up["level"] == down["level"] == 2


def test_skip_llm_governor_early_interview_is_false():
    state = make_v4_state(question_number=1)
    assert should_skip_llm_governor(state) is False


def test_skip_llm_governor_decisive_read_after_question_four():
    state = make_v4_state(
        question_number=5,
        hypothesis_target={"status": "confirmed", "confidence": 0.9},
    )
    assert should_skip_llm_governor(state) is True


def test_skip_llm_governor_uncertain_read_keeps_llm():
    state = make_v4_state(
        question_number=5,
        hypothesis_target={"status": "testing", "confidence": 0.5},
    )
    assert should_skip_llm_governor(state) is False


async def test_governor_deterministic_path_writes_profile(monkeypatch):
    class FailLLM:
        async def invoke(self, prompt, **kwargs):
            raise Exception("LLM down")

    monkeypatch.setattr("app.services.llm_service.get_llm_service", lambda: FailLLM())
    state = make_v4_state(
        evidence_store=[
            {"id": "e1", "question_number": 1, "score": 3.0, "competency": "tech_core"},
        ],
        hypothesis_target={"confidence": 0.2, "status": "testing"},
    )
    state["difficulty_level"] = 3
    result = await difficulty_governor(state, use_llm=True)
    assert result["difficulty_delta"] == -1
    assert result["difficulty_profile"]["level"] == 2
    assert result["difficulty_profile"]["delta"] == -1


# ---------------------------------------------------------------------------
# Evidence graph
# ---------------------------------------------------------------------------

def test_evidence_graph_links_evidence_to_hypotheses():
    hyps = refutable_hypotheses(1)
    hyps[0]["id"] = "h0"
    evidence = [
        {"id": "e1", "competency": "tech_core", "score": 8.0, "evidence_text": "strong tech_core answer"},
    ]
    graph = update_evidence_graph({}, evidence, hyps)
    assert "e1->h0" in graph["edges"]
    assert graph["edges"]["e1->h0"]["support"] is True
    assert graph["nodes"]["tech_core"]["average_score"] == 8.0


def test_evidence_graph_marks_contradiction():
    hyps = [{"id": "h0", "statement": "Candidate has strong tech_core skills",
             "direction": "positive", "status": "testing", "confidence": 0.5}]
    evidence = [{"id": "e1", "competency": "tech_core", "score": 2.0, "evidence_text": "weak"}]
    graph = update_evidence_graph({}, evidence, hyps)
    assert graph["edges"]["e1->h0"]["support"] is False


async def test_evidence_extractor_node_builds_graph(fake_evidence_repo):
    state = make_v4_state(
        current_question="Test question?",
        candidate_answer="My answer.",
        question_objective={"target_competency": "tech_core"},
        unified_evaluation={"technical": {"score": 8.0, "evidence": "solid", "confidence": 0.9}},
        hypotheses=refutable_hypotheses(1),
    )
    state["hypotheses"][0]["id"] = "h0"
    result = await evidence_extractor_node(state)
    assert result["evidence_graph"]["nodes"]
    assert result["evidence_graph"]["edges"]
    assert result["evidence_store"]


def test_report_exposes_evidence_graph_and_difficulty_profile():
    state = make_v4_state(
        evidence_store=[{"id": "e1"}],
        evidence_graph={"nodes": {"tech_core": {}}, "edges": {"e1->h0": {}}},
        difficulty_profile={"level": 2, "dimensions": []},
    )
    report = build_report_response(state)
    assert report["evidence_graph"]["competency_nodes"] == 1
    assert report["evidence_graph"]["evidence_edges"] == 1
    assert report["difficulty_profile"]["level"] == 2


def test_report_separates_performance_coverage_and_progress():
    """D3: the per-answer average, the competency coverage and the question
    progress are three different numbers — the report must expose each with
    its own semantics so 73% coverage can never be read as 6-of-10 asked."""
    state = make_v4_state(
        question_number=6,
        total_questions=10,
        evidence_store=[
            {"id": f"e{i}", "question_number": i + 1, "score": s}
            for i, s in enumerate([7.69, 8.50, 8.59, 6.38, 7.25, 7.72])
        ],
        hiring_recommendation={
            "verdict": "strong_hire",
            "confidence": 0.9,
            "composite_score": 8.62,
            "coverage_ratio": 0.73,
        },
        difficulty_profile={"level": 1, "label": "foundational", "score": 1.0},
    )
    report = build_report_response(state)
    perf = report["interview_performance"]
    assert perf["average_answer_score"] == 7.69
    assert [t["score"] for t in perf["score_timeline"]] == [7.69, 8.50, 8.59, 6.38, 7.25, 7.72]
    progress = report["question_progress"]
    assert progress == {"answered": 6, "planned": 10, "ratio": 0.6}
    assert report["coverage"]["competency_coverage_ratio"] == 0.73
    assert report["difficulty_reached"] == 1
    assert report["hiring_recommendation"]["composite_score"] == 8.62
    assert "not the per-answer average" in report["hiring_recommendation"]["composite_score_note"]
    assert "not the question-answered ratio" in report["coverage"]["note"]
