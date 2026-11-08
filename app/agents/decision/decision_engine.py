"""V5 decision engine — deterministic 7-point hiring decision (Fix 9, plan step 3).

One decision function: the score is the canonical score (the weighted competency average,
``contradiction_engine.compute_canonical_score``) minus a contradiction penalty — nothing else.
Coverage, difficulty, evidence volume and substantiation act only as **caps** on the label
(``apply_decision_caps``), each recorded in ``adjustments`` with its reason, so a report can always
say why a verdict is what it is. Before step 3 the score multiplied a difficulty credit and added
coverage / confirmed-hypothesis terms on top of a composite that already contained them.

Scale (by decision score, 0..10; calibrated at the step 3 gate):
    strong_hire        >= 8.0
    hire               >= 7.0
    lean_hire          >= 6.2
    insufficient_evidence  >= 5.0  (borderline — probe round recommended)
    lean_no_hire       >= 4.0
    no_hire            >= 2.5
    strong_no_hire     < 2.5
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
HIRE_SIDE = {"strong_hire", "hire", "lean_hire"}

# Label thresholds on the decision score (plan step 3). Recalibrate only by the plan's rule: strong
# clears hire by >= 0.3 and weak falls below 5.0 — never tuned to push a particular persona down.
DECISION_THRESHOLDS = (
    (8.0, "strong_hire"),
    (7.0, "hire"),
    (6.2, "lean_hire"),
    (5.0, "insufficient_evidence"),
    (4.0, "lean_no_hire"),
    (2.5, "no_hire"),
)

# Caps (F4 / P4): coverage is the amount of the role actually tested.
STRONG_HIRE_MIN_COVERAGE = 0.85
HIRE_MIN_COVERAGE = 0.75
HIRE_SIDE_MIN_COVERAGE = 0.5
# A hire-side verdict needs the candidate tested at the role's level. This replaces the old
# multiplicative difficulty credit: an un-escalated candidate is kept off the top labels, not scored down.
MIN_HIRE_DIFFICULTY = 3
# Plan step 4 cap 6: when at least half the answers were unsubstantiated, a hire-side verdict needs a probe.
MAX_UNSUBSTANTIATED_SHARE_FOR_HIRE = 0.5
# Cap 7b: this many changed figures in one interview (any status) hold a hire-side verdict for a probe round.
MAX_CHANGED_FIGURES_FOR_HIRE = 3

__all__ = [
    "MIN_EVIDENCE_FOR_DECISION",
    "BORDERLINE_CONTRADICTION_CAP",
    "DECISION_SCALE",
    "DECISIVE_DECISIONS",
    "HIRE_SIDE",
    "DECISION_THRESHOLDS",
    "compute_decision_score",
    "map_decision",
    "demote_to",
    "apply_decision_caps",
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
    """The 0..10 decision score: the canonical score minus a contradiction penalty.

    ``coverage_ratio``, ``confirmed_ratio`` and ``difficulty_reached`` are accepted for compatibility but
    are NOT scored — they gate the label through ``apply_decision_caps``. Counting them here again was the
    double-count that pulled honest, un-escalated candidates 1-2 points below their own answers.
    """
    score = _safe(holistic_score)
    if int(contradiction_count or 0) >= BORDERLINE_CONTRADICTION_CAP:
        score -= 1.5 * min(int(contradiction_count), 3) / 3.0
    return round(max(0.0, min(10.0, score)), 2)


def map_decision(score: float) -> str:
    """Map a decision score onto the 7-point scale."""
    score = _safe(score)
    for threshold, label in DECISION_THRESHOLDS:
        if score >= threshold:
            return label
    return "strong_no_hire"


def _rank(label: str) -> int:
    if label in DECISION_SCALE:
        return DECISION_SCALE.index(label)
    return DECISION_SCALE.index("insufficient_evidence")


def demote_to(decision: str, ceiling: str) -> str:
    """The worse of ``decision`` and ``ceiling`` — a cap never improves a verdict."""
    return decision if _rank(decision) >= _rank(ceiling) else ceiling


def apply_decision_caps(decision: str, signals: dict) -> tuple[str, list[dict]]:
    """Apply the ordered caps to a score-based label.

    Every cap that changes the label appends ``{rule, from, to, reason}``. Order (plan step 3):
    1 evidence volume; 2-4 coverage; 5 difficulty at the role's level; 6 unsubstantiated share;
    7 claim conflicts (one unexplained: hire-side -> insufficient_evidence; two or an admitted
    inflation: at most lean_no_hire, whatever the score).
    """
    adjustments: list[dict] = []

    def cap(rule: str, ceiling: str, reason: str) -> None:
        nonlocal decision
        lowered = demote_to(decision, ceiling)
        if lowered != decision:
            adjustments.append({"rule": rule, "from": decision, "to": lowered, "reason": reason})
            decision = lowered

    evidence_count = int(signals.get("evidence_count") or 0)
    coverage = _safe(signals.get("coverage_ratio"), 0.0)
    difficulty = _safe(signals.get("difficulty_reached"), 0)
    role_floor = int(_safe(signals.get("role_floor"), 1))
    unsub = signals.get("unsubstantiated_share")

    # 1. Too little evidence to decide anything, in either direction.
    if evidence_count < MIN_EVIDENCE_FOR_DECISION and decision != "insufficient_evidence":
        adjustments.append({
            "rule": "evidence_count", "from": decision, "to": "insufficient_evidence",
            "reason": f"only {evidence_count} evidence item(s); need {MIN_EVIDENCE_FOR_DECISION}",
        })
        decision = "insufficient_evidence"

    if decision in HIRE_SIDE:
        # 2-4. Coverage of the role.
        if decision == "strong_hire" and coverage < STRONG_HIRE_MIN_COVERAGE:
            cap("coverage", "hire", f"coverage {coverage:.0%} < {STRONG_HIRE_MIN_COVERAGE:.0%} for strong_hire")
        if coverage < HIRE_SIDE_MIN_COVERAGE:
            cap("coverage", "insufficient_evidence",
                f"coverage {coverage:.0%} < {HIRE_SIDE_MIN_COVERAGE:.0%}: most of the role was not tested")
        elif coverage < HIRE_MIN_COVERAGE:
            cap("coverage", "lean_hire", f"coverage {coverage:.0%} < {HIRE_MIN_COVERAGE:.0%}")
        # 5. Tested at the role's level.
        needed = max(MIN_HIRE_DIFFICULTY, role_floor + 1)
        if difficulty < needed:
            cap("difficulty", "lean_hire",
                f"not tested at the role's level: difficulty reached {difficulty:.0f} < {needed}")
        # 6. Substantiation.
        if unsub is not None and _safe(unsub) >= MAX_UNSUBSTANTIATED_SHARE_FOR_HIRE:
            cap("unsubstantiated", "insufficient_evidence",
                f"{_safe(unsub):.0%} of answers were unsubstantiated; probe the claims before hiring")

    # 7. Claim conflicts (plan step 5): figures the candidate changed and never explained. Only
    # open / asked / unexplained conflicts count; explained ones never block a hire.
    conflicts = int(signals.get("unexplained_claim_conflicts") or 0)
    if signals.get("inflation_admitted") or conflicts >= 2:
        cap("claim_conflict", "lean_no_hire",
            "the candidate admitted a figure was inflated" if signals.get("inflation_admitted")
            else f"{conflicts} figures changed during the interview and were not explained")
    elif conflicts == 1 and decision in HIRE_SIDE:
        cap("claim_conflict", "insufficient_evidence",
            "a figure changed during the interview and was not explained; reconcile it before hiring")

    # 7b. The pattern (user decision after step 6): one or two changed figures, once explained, never count —
    # but 3+ changed figures in one interview, explained or not, need a probe round before a hire. In the step 6
    # gate the bluffer changed 3-4 figures per interview and explained each fluently; strong changed 0-1.
    total = int(signals.get("claim_conflicts_total") or 0)
    if total >= MAX_CHANGED_FIGURES_FOR_HIRE and decision in HIRE_SIDE:
        cap("claim_pattern", "insufficient_evidence",
            f"{total} figures changed during the interview; even explained, probe them before hiring")

    return decision, adjustments


def decide_hiring_decision(
    *,
    holistic_score: Any = None,
    coverage_ratio: Any = None,
    confirmed_ratio: Any = None,
    contradiction_count: int = 0,
    difficulty_reached: Any = None,
    evidence_count: int = 0,
    role_floor: int = 1,
    unsubstantiated_share: Any = None,
    unexplained_claim_conflicts: int = 0,
    inflation_admitted: bool = False,
    claim_conflicts_total: int = 0,
) -> dict:
    """Deterministic 7-point hiring decision with full rationale.

    Returns ``{decision, draft_decision, decision_score, signals, adjustments, rationale, flag_review}``:
    ``draft_decision`` is the score's label before any cap, ``decision`` the label after the caps.
    """
    score = compute_decision_score(holistic_score=holistic_score, contradiction_count=contradiction_count)
    signals = {
        "coverage_ratio": round(_safe(coverage_ratio, 0.0), 4),
        "confirmed_ratio": round(_safe(confirmed_ratio, 0.0), 4),
        "contradiction_count": int(contradiction_count or 0),
        "difficulty_reached": _safe(difficulty_reached, 0),
        "evidence_count": int(evidence_count or 0),
        "role_floor": int(_safe(role_floor, 1)),
        "unsubstantiated_share": (
            round(_safe(unsubstantiated_share), 3) if unsubstantiated_share is not None else None
        ),
        "unexplained_claim_conflicts": int(unexplained_claim_conflicts or 0),
        "inflation_admitted": bool(inflation_admitted),
        "claim_conflicts_total": int(claim_conflicts_total or 0),
    }
    draft = map_decision(score)
    decision, adjustments = apply_decision_caps(draft, signals)
    # Compatibility: report and harness readers know ``coverage_capped``.
    signals["coverage_capped"] = next((a["reason"] for a in adjustments if a["rule"] == "coverage"), "")

    rationale = (
        f"Deterministic 7-point decision: score {score}/10 (weighted competency average "
        f"{_safe(holistic_score):.2f}, {signals['contradiction_count']} serious contradiction(s)); "
        f"coverage {signals['coverage_ratio']:.0%}, difficulty reached {signals['difficulty_reached']:.0f}."
    )
    if adjustments:
        rationale += " " + " ".join(f"Capped {a['from']} -> {a['to']}: {a['reason']}." for a in adjustments)

    return {
        "decision": decision,
        "draft_decision": draft,
        "decision_score": score,
        "decision_scale": "7_point",
        "signals": signals,
        "adjustments": adjustments,
        "flag_review": any(a["rule"] in ("coverage", "evidence_count") for a in adjustments),
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
