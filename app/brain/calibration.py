"""Hiring Calibration Brain V5.

Never "score > 8 = hire". Quality is calibrated against:

    competency strength + evidence quantity + difficulty reached
    + confidence - contradictions

A candidate scoring 9 at difficulty 1 with 5 evidence records is riskier than
one scoring 8 at difficulty 4 with 15. This layer computes the calibrated
quality, an evidence-depth label and a decision confidence — all
deterministic inputs to the final decision.
"""
import logging

logger = logging.getLogger(__name__)

DEPTH_THRESHOLDS = {"low": 6, "medium": 10}


def evidence_depth(total_evidence: int) -> str:
    if total_evidence >= DEPTH_THRESHOLDS["medium"]:
        return "high"
    if total_evidence >= DEPTH_THRESHOLDS["low"]:
        return "medium"
    return "low"


def calibrated_quality(
    *,
    composite_score: float,
    total_evidence: int,
    difficulty_reached: int,
    role_floor: int | None,
    proof_ratio: float,
    resolved_ratio: float,
    serious_contradictions: int,
) -> float:
    """Calibrated 0..10 quality score.

    The base composite (competency strength) is nudged by evidence quantity,
    difficulty reached and resolution confidence, then penalized for
    contradictions. Never exceeds the base by more than 1.0 and never grants
    senior-graded credit below the role floor.
    """
    base = float(composite_score or 0.0)

    depth = evidence_depth(total_evidence)
    evidence_credit = {"low": 0.0, "medium": 0.3, "high": 0.5}[depth]

    difficulty_credit = 0.0
    if role_floor is not None:
        if difficulty_reached >= role_floor:
            difficulty_credit = min(0.4, 0.1 * (difficulty_reached - role_floor + 1))
        else:
            difficulty_credit = -0.4
    else:
        difficulty_credit = min(0.3, 0.1 * max(0, difficulty_reached - 1))

    confidence_credit = 0.0 if resolved_ratio < 0.3 else min(0.3, resolved_ratio * 0.3)

    contradiction_penalty = min(0.4, 0.1 * serious_contradictions)

    calibrated = base + evidence_credit + difficulty_credit + confidence_credit - contradiction_penalty

    if total_evidence < DEPTH_THRESHOLDS["low"] and calibrated > 7.0:
        calibrated = 7.0
    if proof_ratio < 0.35 and calibrated > 6.5:
        calibrated = 6.5

    return round(max(0.0, min(10.0, calibrated)), 2)


def decision_confidence(
    *,
    base_confidence: float,
    proof_ratio: float,
    evidence_depth_label: str,
) -> float:
    """Blend hypothesis confidence with how much of the evidence was PROVEN.

    Claim-heavy interviews cannot carry the same confidence as proof-heavy
    ones even if the raw score is identical.
    """
    depth_factor = {"low": 0.85, "medium": 0.95, "high": 1.0}[evidence_depth_label]
    blended = float(base_confidence or 0.5) * (0.5 + 0.5 * proof_ratio) * depth_factor
    return round(max(0.0, min(1.0, blended)), 3)


def build_calibration_state(
    *,
    hiring_recommendation: dict,
    difficulty_reached: int,
    role_floor: int | None,
    total_evidence: int,
    proof_ratio: float,
    resolved_ratio: float,
    serious_contradictions: int,
) -> dict:
    """Assemble the calibration brain section."""
    rec = hiring_recommendation or {}
    composite = float(rec.get("composite_score") or 0.0)
    base_conf = float(rec.get("confidence_v2") or rec.get("confidence") or 0.5)
    depth = evidence_depth(total_evidence)

    score = calibrated_quality(
        composite_score=composite,
        total_evidence=total_evidence,
        difficulty_reached=difficulty_reached,
        role_floor=role_floor,
        proof_ratio=proof_ratio,
        resolved_ratio=resolved_ratio,
        serious_contradictions=serious_contradictions,
    )
    conf = decision_confidence(
        base_confidence=base_conf,
        proof_ratio=proof_ratio,
        evidence_depth_label=depth,
    )

    verdict = rec.get("verdict")
    if difficulty_reached < 3 and verdict in ("strong_hire", "hire"):
        verdict = "borderline"

    return {
        "calibrated_score": score,
        "raw_composite": round(composite, 2),
        "evidence_depth": depth,
        "total_evidence": total_evidence,
        "proof_ratio": round(proof_ratio, 4),
        "difficulty_reached": difficulty_reached,
        "role_floor": role_floor,
        "calibrated_verdict": verdict,
        "decision_confidence": conf,
        "contradiction_penalty": serious_contradictions,
    }