"""Decision Intelligence V5 — the final brain layer.

Wraps the deterministic hiring decision and the calibration brain into the
``decision_state`` the report and the memory layer read. Single source of
truth: ``hiring_decision.decision`` (deterministic) is authoritative.
"""
import logging

logger = logging.getLogger(__name__)


def build_decision_state(
    *,
    hiring_decision: dict,
    hiring_recommendation: dict,
    calibration_state: dict,
) -> dict:
    hd = hiring_decision or {}
    cal = calibration_state or {}
    decision = hd.get("decision") or (hiring_recommendation or {}).get("verdict") or "insufficient_evidence"
    decision_score = hd.get("decision_score")
    if decision_score is None and (hiring_recommendation or {}).get("composite_score") is not None:
        decision_score = hiring_recommendation["composite_score"]

    risks = []
    if cal.get("difficulty_reached", 0) and cal.get("role_floor"):
        if int(cal.get("difficulty_reached") or 0) < int(cal.get("role_floor") or 0):
            risks.append("never tested at the role's difficulty floor")
    if cal.get("proof_ratio", 1.0) < 0.4:
        risks.append("evidence largely claimed, not proven")
    if cal.get("evidence_depth") == "low":
        risks.append("low evidence volume")
    if cal.get("contradiction_penalty", 0) >= 2:
        risks.append("serious contradictions in evidence")

    return {
        "decision": decision,
        "decision_score": decision_score,
        "confidence": cal.get("decision_confidence") or hd.get("confidence") or 0.0,
        "calibrated_score": cal.get("calibrated_score"),
        "risk_flags": risks,
        "recommendation_verdict": (hiring_recommendation or {}).get("verdict"),
        "decision_reasoning": (hd.get("rationale") or hd.get("reasoning") or ""),
        "source": "deterministic",
    }