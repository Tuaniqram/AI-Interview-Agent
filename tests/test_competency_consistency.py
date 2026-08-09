"""Competency consistency — one competency id space across evidence, hypotheses,
coverage, and the hiring decision.

Regression for the scorecard demo where every answer scored 8.0-8.6 yet the
verdict was ``insufficient_evidence`` (coverage 0.36): evidence for the
session's own ids (``communication``, ``system_design``) was being relabeled
through the alias map into default-taxonomy ids (``behav_communication``,
``exp_project_depth``), which starved the required competencies of evidence.
"""
import pytest

from app.agents.decision.decision_review import finalize_decision, review_decision
from app.agents.reasoning.contradiction_engine import (
    decide_next_action,
    evaluate_sufficiency,
)
from app.agents.reasoning.evidence_engine import build_candidate_evidence
from app.agents.reasoning.hypothesis_engine import generate_initial_hypotheses

SCORECARD_TAXONOMY = [
    {"id": "problem_solvin", "name": "Problem Solving", "category": "technical", "weight": 2.0, "default_min_evidence": 2},
    {"id": "communication", "name": "Communication", "category": "communication", "weight": 2.0, "default_min_evidence": 2},
    {"id": "system_design", "name": "System Design", "category": "technical", "weight": 1.5, "default_min_evidence": 2},
]

REQUIRED = ["problem_solvin", "communication", "system_design"]

WEIGHTS = {"problem_solvin": 2.0, "communication": 2.0, "system_design": 1.5}


def _evaluation(top_dim="technical", score=8.0):
    return {
        top_dim: {"score": score, "confidence": 0.9, "evidence": "I built it", "strengths": [], "weaknesses": []},
    }


def test_evidence_preserves_session_taxonomy_communication():
    records = build_candidate_evidence(
        evaluation=_evaluation(top_dim="communication"),
        question="Tell me about your communication experience",
        question_number=1,
        session_id="s1",
        question_objective={"target_competency": "communication"},
        competency_taxonomy=SCORECARD_TAXONOMY,
    )
    assert records
    assert all(r["competency"] == "communication" for r in records)


def test_evidence_preserves_session_taxonomy_system_design():
    records = build_candidate_evidence(
        evaluation=_evaluation(top_dim="technical"),
        question="Walk me through a system design",
        question_number=1,
        session_id="s1",
        question_objective={"target_competency": "system_design"},
        competency_taxonomy=SCORECARD_TAXONOMY,
    )
    assert records
    assert all(r["competency"] == "system_design" for r in records)


def test_evidence_still_alias_normalizes_free_text_outside_session():
    records = build_candidate_evidence(
        evaluation=_evaluation(),
        question="Tell me about project management",
        question_number=1,
        session_id="s1",
        question_objective={"target_competency": "project management"},
        competency_taxonomy=SCORECARD_TAXONOMY,
    )
    assert records
    assert all(r["competency"] == "exp_project_depth" for r in records)


def test_hypothesis_seeding_stays_in_session_set():
    hyps = generate_initial_hypotheses(
        "Senior Frontend Engineer",
        candidate_profile={
            "strengths": ["React", "system design", "async debugging"],
            "weaknesses": ["limited exposure to senior architecture"],
        },
        max_hypotheses=6,
        competency_taxonomy=SCORECARD_TAXONOMY,
    )
    assert hyps
    assert all(h["competency"] in set(REQUIRED) for h in hyps)


def test_fully_covered_scorecard_yields_sufficient_high_verdict():
    summary = {
        "problem_solvin": {"evidence_count": 3, "average_score": 8.33, "gap": 0.0},
        "communication": {"evidence_count": 3, "average_score": 8.67, "gap": 0.0},
        "system_design": {"evidence_count": 3, "average_score": 8.33, "gap": 0.0},
    }
    sufficiency, rec = evaluate_sufficiency(
        summary,
        REQUIRED,
        [],
        [{"status": "confirmed"}, {"status": "confirmed"}, {"status": "confirmed"}, {"status": "testing"}],
        question_number=9,
        comp_weights=WEIGHTS,
        difficulty_reached=4,
        unanswered_hypotheses=1,
    )
    assert sufficiency["is_sufficient"] is True
    assert sufficiency["coverage_ratio"] >= 0.5
    assert rec["coverage_ratio"] >= 0.5
    assert rec["verdict"] not in ("insufficient_evidence", "reject")
    assert rec["composite_score"] >= 7.5


def test_finish_and_review_agree_on_covered_scorecard():
    summary = {
        "problem_solvin": {"evidence_count": 3, "average_score": 8.33, "gap": 0.0, "average_confidence": 0.9},
        "communication": {"evidence_count": 3, "average_score": 8.67, "gap": 0.0, "average_confidence": 0.9},
        "system_design": {"evidence_count": 3, "average_score": 8.33, "gap": 0.0, "average_confidence": 0.9},
    }
    sufficiency, rec = evaluate_sufficiency(
        summary,
        REQUIRED,
        [],
        [{"status": "confirmed"}, {"status": "confirmed"}, {"status": "confirmed"}, {"status": "testing"}],
        question_number=9,
        comp_weights=WEIGHTS,
    )
    action = decide_next_action(
        summary, REQUIRED, sufficiency, [], question_number=9,
        hypotheses=[{"competency": c, "status": "confirmed"} for c in REQUIRED]
        + [{"competency": "system_design", "status": "testing"}],
    )
    assert action == "finish"

    evidence = [
        {"strength": 0.72, "contradiction": False},
        {"strength": 0.72, "contradiction": False},
        {"strength": 0.72, "contradiction": False},
        {"strength": 0.72, "contradiction": False},
        {"strength": 0.72, "contradiction": False},
        {"strength": 0.72, "contradiction": False},
    ]
    state = {
        "hiring_recommendation": rec,
        "competency_summary": summary,
        "evidence_store": evidence,
    }
    draft = {"decision": rec["verdict"], "confidence": 0.8}
    checks = review_decision(draft, state)
    assert not any(c["issue"] == "missing_competency" and c["severity"] == "high" for c in checks)
    final = finalize_decision(draft, checks)
    assert final["decision"] != "insufficient_evidence"
    assert final["demoted_to_undecided"] is False


def test_finish_requires_coverage_breadth_and_difficulty_floor():
    """V5 role gates: a fully covered single competency must NOT finish a
    senior interview while the rest of the blueprint is untested (the demo
    regression: coverage 1.0 at question 5 on a 1-competency required set)."""
    summary = {
        "tech_system_design": {"evidence_count": 4, "average_score": 8.5, "gap": 0.0},
        "tech_deployment": {"evidence_count": 0, "average_score": 0.0, "gap": 1.0},
        "tech_event_driven": {"evidence_count": 0, "average_score": 0.0, "gap": 1.0},
    }
    required = ["tech_system_design", "tech_deployment", "tech_event_driven"]
    sufficiency, _ = evaluate_sufficiency(
        summary,
        required,
        [],
        [],
        question_number=5,
        comp_weights={c: 1.0 for c in required},
        difficulty_reached=3,
    )
    assert sufficiency["coverage_ratio"] == pytest.approx(1 / 3, abs=0.005)  # the honest 33% — not 100%

    # Sufficiency alone no longer finishes: coverage is 33% < 80%.
    action = decide_next_action(
        summary, required, sufficiency, [], question_number=5,
        hypotheses=[],
        difficulty_reached=3,
        difficulty_floor=3,
    )
    assert action != "finish"

    # Same profile fully covered across the blueprint AND at the role floor.
    full = {
        "tech_system_design": {"evidence_count": 3, "average_score": 8.5, "gap": 0.0},
        "tech_deployment": {"evidence_count": 2, "average_score": 8.0, "gap": 0.0},
        "tech_event_driven": {"evidence_count": 2, "average_score": 8.0, "gap": 0.0},
    }
    suff_full, _ = evaluate_sufficiency(
        full, required, [], [], question_number=8,
        comp_weights={c: 1.0 for c in required},
        difficulty_reached=3,
    )
    assert suff_full["coverage_ratio"] >= 0.8
    action_full = decide_next_action(
        full, required, suff_full, [], question_number=8,
        hypotheses=[{"competency": c, "status": "confirmed"} for c in required],
        difficulty_reached=3,
        difficulty_floor=3,
    )
    assert action_full == "finish"

    # But a session stuck below the senior floor must keep going.
    action_low_diff = decide_next_action(
        full, required, suff_full, [], question_number=8,
        hypotheses=[{"competency": c, "status": "confirmed"} for c in required],
        difficulty_reached=1,
        difficulty_floor=3,
    )
    assert action_low_diff != "finish"


def test_relabeled_evidence_keeps_coverage_low():
    """Guard: evidence living under default-taxonomy ids must NOT inflate the
    required competencies' coverage (the pre-fix behavior that mis-verdicts)."""
    summary = {
        "problem_solvin": {"evidence_count": 3, "average_score": 8.33, "gap": 0.0},
        "behav_communication": {"evidence_count": 3, "average_score": 8.67, "gap": 0.0},
        "exp_project_depth": {"evidence_count": 3, "average_score": 8.33, "gap": 0.0},
    }
    sufficiency, _ = evaluate_sufficiency(
        summary,
        REQUIRED,
        [],
        [],
        question_number=9,
        comp_weights=WEIGHTS,
    )
    assert sufficiency["coverage_ratio"] < 0.5
