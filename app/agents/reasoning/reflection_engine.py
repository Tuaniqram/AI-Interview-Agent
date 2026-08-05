"""V5 reflection engine — orchestration over the pure contradiction capability
in ``app.agents.reasoning.contradiction_engine``.

Kept as a node-shaped wrapper (state in → state out) so the engine imports it
unchanged; all detection/sufficiency/action math lives in the capability module.
"""
import logging

from app.core.interview_state import InterviewState
from app.agents.reasoning.contradiction_engine import (
    _DEFAULT_REQUIRED,
    COVERAGE_THRESHOLD,
    MIN_QUESTIONS_PER_COMPETENCY,
    MAX_CONSECUTIVE_SAME_DIMENSION,
    SUFFICIENCY_GAP_THRESHOLD,
    average_evidence_confidence,
    competency_weights,
    decide_next_action,
    detect_contradictions,
    evaluate_sufficiency,
    unanswered_hypothesis_count,
)

logger = logging.getLogger(__name__)


async def reflection_engine(state: InterviewState) -> InterviewState:
    competency_summary = state.get("competency_summary", {})
    required_competencies = state.get("required_competencies", _DEFAULT_REQUIRED)
    comp_weights = competency_weights(state)
    existing_contradictions = state.get("contradictions", [])
    existing_consistency = state.get("consistency_checks", [])
    hypotheses = state.get("hypotheses", [])
    unified_evaluation = state.get("unified_evaluation", {})
    question_number = state.get("question_number", 0)

    contradictions, consistency_checks = detect_contradictions(
        competency_summary, existing_contradictions, existing_consistency,
        unified_evaluation,
    )

    difficulty_reached = state.get("difficulty_level")
    unanswered = unanswered_hypothesis_count(hypotheses)

    evidence_sufficiency, hiring_recommendation = evaluate_sufficiency(
        competency_summary, required_competencies, contradictions, hypotheses,
        question_number, comp_weights,
        difficulty_reached=difficulty_reached,
        unanswered_hypotheses=unanswered,
    )

    next_action = decide_next_action(
        competency_summary, required_competencies, evidence_sufficiency,
        contradictions, question_number, hypotheses,
        difficulty_reached=difficulty_reached,
        unanswered_hypotheses=unanswered,
    )

    reflection_inputs = {
        "coverage_ratio": evidence_sufficiency.get("coverage_ratio", 0.0),
        "average_confidence": average_evidence_confidence(competency_summary),
        "difficulty_reached": difficulty_reached,
        "unanswered_hypotheses": unanswered,
        "budget_remaining": max(0, int(state.get("max_questions", 14) or 14) - question_number),
        "contradiction_count": len(contradictions),
    }

    return {
        **state,
        "contradictions": contradictions,
        "consistency_checks": consistency_checks,
        "evidence_sufficiency": evidence_sufficiency,
        "hiring_recommendation": hiring_recommendation,
        "reflection_action": next_action,
        "reflection_inputs": reflection_inputs,
    }
