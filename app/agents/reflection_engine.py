import logging
from uuid import uuid4
from datetime import datetime, timezone

from app.graph.interview_state import InterviewState
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY

_DEFAULT_REQUIRED = [c["id"] for c in COMPETENCY_TAXONOMY]

logger = logging.getLogger(__name__)

COVERAGE_THRESHOLD = 0.7
MIN_QUESTIONS_PER_COMPETENCY = 2
MAX_CONSECUTIVE_SAME_DIMENSION = 2
SUFFICIENCY_GAP_THRESHOLD = 0.3


async def reflection_engine(state: InterviewState) -> InterviewState:
    competency_summary = state.get("competency_summary", {})
    required_competencies = state.get("required_competencies", _DEFAULT_REQUIRED)
    comp_weights = _competency_weights(state)
    existing_contradictions = state.get("contradictions", [])
    existing_consistency = state.get("consistency_checks", [])
    hypotheses = state.get("hypotheses", [])
    unified_evaluation = state.get("unified_evaluation", {})
    question_number = state.get("question_number", 0)

    contradictions, consistency_checks = _detect_contradictions(
        competency_summary, existing_contradictions, existing_consistency,
        unified_evaluation,
    )

    evidence_sufficiency, hiring_recommendation = _evaluate_sufficiency(
        competency_summary, required_competencies, contradictions, hypotheses, question_number,
        comp_weights,
    )

    next_action = _decide_next_action(
        competency_summary, required_competencies, evidence_sufficiency,
        contradictions, question_number, hypotheses,
    )

    return {
        **state,
        "contradictions": contradictions,
        "consistency_checks": consistency_checks,
        "evidence_sufficiency": evidence_sufficiency,
        "hiring_recommendation": hiring_recommendation,
        "reflection_action": next_action,
    }


def _competency_weights(state: InterviewState) -> dict[str, float]:
    taxonomy = state.get("competency_taxonomy") or COMPETENCY_TAXONOMY
    weights = {}
    for c in taxonomy:
        weight = c.get("weight")
        weights[c["id"]] = float(weight) if weight else 1.0
    return weights


def _detect_contradictions(
    competency_summary: dict,
    existing_contradictions: list,
    existing_consistency: list,
    unified_evaluation: dict,
) -> tuple[list, list]:
    contradictions = list(existing_contradictions)
    consistency_checks = list(existing_consistency)

    evaluation = unified_evaluation or {}
    for dim, data in evaluation.items():
        if not isinstance(data, dict):
            continue
        score = data.get("score")
        if score is None:
            continue
        evidence = data.get("evidence", "")
        confidence = data.get("confidence", 0.5)

        if score >= 7.0 and confidence >= 0.3:
            consistency_checks.append({
                "type": dim,
                "assessment": "positive",
                "score": score,
                "confidence": confidence,
                "evidence": evidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    for comp, summary in competency_summary.items():
        scores = summary.get("scores", [])
        if len(scores) >= 2:
            latest = scores[-1]
            prev = scores[-2]
            if latest is not None and prev is not None and abs(latest - prev) >= 4.0:
                contradiction_id = str(uuid4())
                contradictions.append({
                    "id": contradiction_id,
                    "competency": comp,
                    "type": "score_inconsistency",
                    "statement": f"Inconsistent performance in {comp}: previous score {prev}, latest {latest}",
                    "severity": "medium",
                    "evidence_ids": [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    return contradictions, consistency_checks


def _evaluate_sufficiency(
    competency_summary: dict,
    required_competencies: list[str],
    contradictions: list,
    hypotheses: list,
    question_number: int,
    comp_weights: dict[str, float],
) -> tuple[dict, dict]:
    total_weight = 0.0
    covered_weight = 0.0
    comp_details = {}

    for comp in required_competencies:
        summary = competency_summary.get(comp, {})
        evidence_count = summary.get("evidence_count", 0)
        avg_score = summary.get("average_score", 0.0) or 0.0
        gap = summary.get("gap", 1.0)

        weight = comp_weights.get(comp, 1.0)

        is_covered = evidence_count >= MIN_QUESTIONS_PER_COMPETENCY and gap <= SUFFICIENCY_GAP_THRESHOLD
        if is_covered:
            covered_weight += weight
        total_weight += weight

        comp_details[comp] = {
            "evidence_count": evidence_count,
            "average_score": avg_score,
            "gap": gap,
            "weight": weight,
            "covered": is_covered,
        }

    coverage_ratio = covered_weight / total_weight if total_weight > 0 else 0.0

    serious_contradictions = [c for c in contradictions if c.get("severity") in ("high", "medium")]
    severity = "sufficient" if serious_contradictions else "insufficient"

    if coverage_ratio >= COVERAGE_THRESHOLD and not serious_contradictions and question_number >= 5:
        sufficiency = {
            "is_sufficient": True,
            "coverage_ratio": round(coverage_ratio, 2),
            "covered_weight": covered_weight,
            "total_weight": total_weight,
            "remaining_gaps": sum(1 for d in comp_details.values() if not d["covered"]),
            "severity": "sufficient",
            "details": comp_details,
        }
    else:
        sufficiency = {
            "is_sufficient": False,
            "coverage_ratio": round(coverage_ratio, 2),
            "covered_weight": covered_weight,
            "total_weight": total_weight,
            "remaining_gaps": sum(1 for d in comp_details.values() if not d["covered"]),
            "severity": severity,
            "details": comp_details,
        }

    hypothesis_statuses = {}
    for h in hypotheses:
        st = h.get("status", "untested")
        hypothesis_statuses[st] = hypothesis_statuses.get(st, 0) + 1

    confirmed = hypothesis_statuses.get("confirmed", 0)
    refuted = hypothesis_statuses.get("refuted", 0)
    testing = hypothesis_statuses.get("testing", 0)

    if coverage_ratio >= COVERAGE_THRESHOLD and confirmed >= refuted and question_number >= 5:
        verdict = "hire"
        confidence = round(min(confirmed / (confirmed + refuted + 1), 0.95), 2) if confirmed > 0 else 0.5
    elif refuted > confirmed and question_number >= 5:
        verdict = "no_hire"
        confidence = round(min(refuted / (confirmed + refuted + 1), 0.95), 2) if refuted > 0 else 0.5
    elif coverage_ratio >= 0.9 and testing == 0:
        verdict = "lean_hire" if confirmed >= refuted else "lean_no_hire"
        confidence = 0.6
    else:
        verdict = "insufficient_evidence"
        confidence = 0.0

    recommendation = {
        "verdict": verdict,
        "confidence": confidence,
        "coverage_ratio": round(coverage_ratio, 2),
        "composite_score": round(
            sum(d["average_score"] * d["weight"] for d in comp_details.values()) / total_weight, 2
        ) if total_weight > 0 else 0.0,
        "confirmed_hypotheses": confirmed,
        "refuted_hypotheses": refuted,
        "testing_hypotheses": testing,
        "contradictions_found": len(contradictions),
    }

    return sufficiency, recommendation


def _decide_next_action(
    competency_summary: dict,
    required_competencies: list[str],
    evidence_sufficiency: dict,
    contradictions: list,
    question_number: int,
    hypotheses: list,
) -> str:
    if evidence_sufficiency.get("is_sufficient"):
        return "finish"

    if question_number <= 2:
        return "probe"

    serious = [c for c in contradictions if c.get("severity") in ("high", "medium")]
    if len(serious) >= 2:
        return "change_competency"

    max_questions = 14  # AURA cap — evidence-driven end usually fires earlier
    if question_number >= max_questions:
        return "finish"

    return "probe"
