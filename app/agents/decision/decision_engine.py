"""V5 decision engine — deterministic 7-point hiring decision (Fix 9).

Replaces the coarse 3-way draft (hire / no_hire / undecided) with a
seven-point scale that survives the evidence review. Pure capability: no LLM,
no DB — the hiring-decision node overlays this on the LLM draft and the
legacy ``hiring_recommendation.verdict`` stays untouched.

Scale (by decision score, 0..10):
    strong_hire        >= 8.5
    hire               >= 7.5
    lean_hire          >= 6.5
    insufficient_evidence  >= 5.0  (borderline — probe round recommended)
    lean_no_hire       >= 4.0
    no_hire            >= 2.5
    strong_no_hire     < 2.5

Signals:
    coverage_ratio        — fraction of required competencies with evidence
    confirmed_ratio       — confirmed / (confirmed + refuted + 1)
    contradiction_count   — serious (high/medium) contradictions
    difficulty_reached    — highest difficulty the candidate was pushed to
    evidence_count        — total evidence items
"""
from typing import Any

MIN_EVIDENCE_FOR_DECISION = 4
BORDERLINE_CONTRADICTION_CAP = 2

DECISION_SCALE = (
    "strong_hire",
    "hire",
    "lean_hire",
    "insufficient_evidence",
    "lean_no_hire",
    "no_hire",
    "strong_no_hire",
)

# Decisive labels — a review finding can demote these to insufficient_evidence.
DECISIVE_DECISIONS = {
    "strong_hire",
    "hire",
    "lean_hire",
    "lean_no_hire",
    "no_hire",
    "strong_no_hire",
}

# F4: verdict caps — coverage is the amount of the role actually tested. A
# candidate who was never pushed across the competency set cannot earn the
# top verdicts no matter how high the scores were: strong_hire needs >=85%
# coverage, hire needs >=75%. Below the caps the verdict is demoted one notch.
STRONG_HIRE_MIN_COVERAGE = 0.85
HIRE_MIN_COVERAGE = 0.75

__all__ = [
    "MIN_EVIDENCE_FOR_DECISION",
    "BORDERLINE_CONTRADICTION_CAP",
    "DECISION_SCALE",
    "DECISIVE_DECISIONS",
    "compute_decision_score",
    "map_decision",
    "decide_hiring_decision",
    "decision_next_steps",
]


def _safe(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_decision_score(
    *,
    holistic_score: Any = None,
    coverage_ratio: Any = None,
    confirmed_ratio: Any = None,
    contradiction_count: int = 0,
    difficulty_reached: Any = None,
) -> float:
    """A single 0..10 score from the interview signals.

    The holistic score anchors the decision; coverage and confirmed hypotheses
    pull it toward the extremes, contradictions pull it back to the middle.

    Difficulty credibility (D2): evidence earned at the top of the scale is
    fully credited; a candidate who was only ever pushed to difficulty 1 gets
    a discounted credit — "difficulty 1 + high score" can no longer produce a
    strong_hire. Credit: 0.55 + 0.09 * difficulty (d1=0.64, d3=0.82, d5=1.0).
    """
    holistic = _safe(holistic_score)
    if not holistic:
        coverage = _safe(coverage_ratio, 0.5)
        holistic = 2.0 + coverage * 8.0

    coverage = _safe(coverage_ratio, 0.5)
    confirmed = _safe(confirmed_ratio, 0.5)
    difficulty = _safe(difficulty_reached, 0)

    difficulty_credit = min(1.0, 0.55 + 0.09 * difficulty)

    score = holistic * difficulty_credit
    score += (coverage - 0.5) * 2.0
    score += (confirmed - 0.5) * 2.0
    if int(contradiction_count or 0) >= BORDERLINE_CONTRADICTION_CAP:
        score -= 1.5 * min(int(contradiction_count), 3) / 3.0
    return round(max(0.0, min(10.0, score)), 2)


def map_decision(score: float) -> str:
    """Map a decision score onto the 7-point scale."""
    score = _safe(score)
    if score >= 8.5:
        return "strong_hire"
    if score >= 7.5:
        return "hire"
    if score >= 6.5:
        return "lean_hire"
    if score >= 5.0:
        return "insufficient_evidence"
    if score >= 4.0:
        return "lean_no_hire"
    if score >= 2.5:
        return "no_hire"
    return "strong_no_hire"


def decide_hiring_decision(
    *,
    holistic_score: Any = None,
    coverage_ratio: Any = None,
    confirmed_ratio: Any = None,
    contradiction_count: int = 0,
    difficulty_reached: Any = None,
    evidence_count: int = 0,
) -> dict:
    """Deterministic 7-point hiring decision with full rationale.

    Returns ``{decision, decision_score, signals, rationale, flag_review}``.
    """
    evidence_count = int(evidence_count or 0)
    difficulty = _safe(difficulty_reached, 0)
    difficulty_credit = min(1.0, 0.55 + 0.09 * difficulty)
    score = compute_decision_score(
        holistic_score=holistic_score,
        coverage_ratio=coverage_ratio,
        confirmed_ratio=confirmed_ratio,
        contradiction_count=contradiction_count,
        difficulty_reached=difficulty_reached,
    )

    if evidence_count < MIN_EVIDENCE_FOR_DECISION:
        decision = "insufficient_evidence"
    else:
        decision = map_decision(score)

    # F4: coverage caps — high scores on a half-tested role are not a
    # strong_hire. Demote one notch when the tested coverage is too thin.
    coverage = _safe(coverage_ratio, 0.0)
    coverage_capped = ""
    if decision == "strong_hire" and coverage < STRONG_HIRE_MIN_COVERAGE:
        decision = "hire"
        coverage_capped = (
            f"strong_hire capped to hire: coverage {coverage:.0%} < "
            f"{STRONG_HIRE_MIN_COVERAGE:.0%}"
        )
    elif decision == "hire" and coverage < HIRE_MIN_COVERAGE:
        decision = "lean_hire"
        coverage_capped = (
            f"hire capped to lean_hire: coverage {coverage:.0%} < {HIRE_MIN_COVERAGE:.0%}"
        )

    signals = {
        "coverage_ratio": round(_safe(coverage_ratio, 0.0), 4),
        "confirmed_ratio": round(_safe(confirmed_ratio, 0.0), 4),
        "contradiction_count": int(contradiction_count or 0),
        "difficulty_reached": _safe(difficulty_reached, 0),
        "evidence_count": evidence_count,
        "coverage_capped": coverage_capped,
    }

    rationale = (
        f"Deterministic 7-point decision: score {score}/10 "
        f"(holistic {_safe(holistic_score):.1f} scaled by difficulty credit "
        f"{difficulty_credit:.2f} at difficulty {signals['difficulty_reached']:.0f}, "
        f"adjusted by coverage {signals['coverage_ratio']:.0%}, confirmed-ratio "
        f"{signals['confirmed_ratio']:.0%}, {signals['contradiction_count']} "
        f"serious contradiction(s))."
    )
    if coverage_capped:
        rationale = f"{rationale} {coverage_capped}."

    return {
        "decision": decision,
        "decision_score": score,
        "decision_scale": "7_point",
        "signals": signals,
        "flag_review": bool(coverage_capped) or evidence_count < MIN_EVIDENCE_FOR_DECISION,
        "rationale": rationale,
    }


def decision_next_steps(decision: str) -> list[str]:
    if decision in ("strong_hire", "hire"):
        return ["schedule follow-up with the hiring manager", "prepare offer discussion"]
    if decision == "lean_hire":
        return ["schedule a focused reference check", "prepare offer discussion with conditions"]
    if decision in ("lean_no_hire", "no_hire", "strong_no_hire"):
        return ["archive candidate profile", "log feedback for interviewer calibration"]
    return ["schedule a short probe round", "compare against other shortlisted candidates"]
