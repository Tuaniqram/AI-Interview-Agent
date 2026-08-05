"""V5 decision review — Evidence → Draft → Self Review → Final.

Finalization must be defensible. After the hiring-decision node produces a
*draft*, this capability reviews it against the collected evidence before it
becomes the *final* decision:

- insufficient evidence — not enough evidence items or low competency coverage
- missing competency — required competencies with a large evidence gap
- overconfidence — high draft confidence on weak / low-strength evidence
- contradictions — conflicting evidence under the same competency

Each review produces an ``{issue, severity, detail}`` check; ``finalize_decision``
applies the findings deterministically (downgrade confidence, demote risky
hire/no-hire verdicts, flag for human review). Pure capability — no DB, no
shared-state mutation.
"""
import logging

logger = logging.getLogger(__name__)

MIN_EVIDENCE_FOR_HIGH_CONFIDENCE = 4
MIN_AVG_STRENGTH_FOR_HIGH_CONFIDENCE = 0.6
MIN_COVERAGE_FOR_DECISION = 0.5
OVERCONFIDENCE_CONFIDENCE_FLOOR = 0.75
SUFFICIENCY_GAP_THRESHOLD = 0.3
REVIEW_SEVERITIES = ("low", "medium", "high")

__all__ = [
    "MIN_EVIDENCE_FOR_HIGH_CONFIDENCE",
    "MIN_AVG_STRENGTH_FOR_HIGH_CONFIDENCE",
    "MIN_COVERAGE_FOR_DECISION",
    "OVERCONFIDENCE_CONFIDENCE_FLOOR",
    "SUFFICIENCY_GAP_THRESHOLD",
    "review_decision",
    "finalize_decision",
    "decision_review_node",
]


def _evidence_stats(state: dict) -> dict:
    evidence = state.get("evidence_store") or []
    if not evidence:
        return {"count": 0, "average_strength": 0.0, "contradictions": 0}

    strengths = [ev.get("strength") for ev in evidence if isinstance(ev.get("strength"), (int, float))]
    avg_strength = round(sum(strengths) / len(strengths), 4) if strengths else 0.0
    contradictions = sum(1 for ev in evidence if ev.get("contradiction"))
    return {
        "count": len(evidence),
        "average_strength": avg_strength,
        "contradictions": contradictions,
    }


def _coverage_ratio(state: dict) -> float | None:
    rec = state.get("hiring_recommendation") or {}
    ratio = rec.get("coverage_ratio")
    if ratio is None:
        summary = state.get("competency_summary") or {}
        if not summary:
            return None
        covered = [c for c, s in summary.items() if int(s.get("evidence_count", 0) or 0) > 0]
        ratio = len(covered) / len(summary) if summary else 0.0
    return round(float(ratio), 4)


def _missing_competencies(state: dict) -> list[str]:
    summary = state.get("competency_summary") or {}
    missing = []
    for comp, s in summary.items():
        count = int(s.get("evidence_count", 0) or 0)
        gap = float(s.get("gap", 1.0) or 1.0)
        if count == 0 or gap >= SUFFICIENCY_GAP_THRESHOLD:
            missing.append(comp)
    return missing


def review_decision(draft: dict, state: dict) -> list[dict]:
    """Self-review the draft decision against the collected evidence.

    Returns a list of ``{issue, severity, detail}`` checks, ordered by severity.
    """
    checks: list[dict] = []
    stats = _evidence_stats(state)
    coverage = _coverage_ratio(state)
    decision = str(draft.get("decision", "undecided"))
    confidence = float(draft.get("confidence", 0.0))

    # 1. Insufficient evidence.
    if stats["count"] == 0:
        checks.append({
            "issue": "insufficient_evidence",
            "severity": "high",
            "detail": "No evidence collected; decision is not grounded in data.",
        })
    elif stats["count"] < MIN_EVIDENCE_FOR_HIGH_CONFIDENCE:
        checks.append({
            "issue": "insufficient_evidence",
            "severity": "medium",
            "detail": f"Only {stats['count']} evidence item(s); need >= {MIN_EVIDENCE_FOR_HIGH_CONFIDENCE}.",
        })

    # 2. Missing competencies / low coverage.
    if coverage is None:
        checks.append({
            "issue": "missing_competency",
            "severity": "medium",
            "detail": "No competency coverage map available to judge sufficiency.",
        })
    elif coverage < MIN_COVERAGE_FOR_DECISION:
        missing = _missing_competencies(state)
        checks.append({
            "issue": "missing_competency",
            "severity": "high",
            "detail": f"Coverage {coverage:.0%} < {MIN_COVERAGE_FOR_DECISION:.0%}; "
                      f"uncovered: {', '.join(missing[:3]) or 'unknown'}.",
        })
    elif _missing_competencies(state):
        checks.append({
            "issue": "missing_competency",
            "severity": "low",
            "detail": "Some competencies remain above the sufficiency gap threshold.",
        })

    # 3. Overconfidence on weak evidence.
    if (
        confidence >= OVERCONFIDENCE_CONFIDENCE_FLOOR
        and stats["average_strength"] < MIN_AVG_STRENGTH_FOR_HIGH_CONFIDENCE
    ):
        checks.append({
            "issue": "overconfidence",
            "severity": "medium",
            "detail": (
                f"Confidence {confidence:.2f} exceeds evidence strength "
                f"{stats['average_strength']:.2f}."
            ),
        })

    # 4. Contradictory evidence.
    if stats["contradictions"] >= 2:
        checks.append({
            "issue": "contradictions",
            "severity": "high",
            "detail": f"{stats['contradictions']} evidence item(s) contradict their competency's prior average.",
        })
    elif stats["contradictions"] == 1:
        checks.append({
            "issue": "contradictions",
            "severity": "low",
            "detail": "One contradictory evidence item detected; consider probing before deciding.",
        })

    return sorted(
        checks,
        key=lambda c: -REVIEW_SEVERITIES.index(c["severity"]),
    )


def finalize_decision(draft: dict, checks: list[dict]) -> dict:
    """Apply review findings to the draft, producing the final decision.

    Downgrades confidence for any finding, demotes a decisive verdict to
    ``undecided`` when evidence is insufficient, and attaches the review
    trail to the returned decision.
    """
    decision = dict(draft)
    original_confidence = float(draft.get("confidence", 0.0))
    confidence = original_confidence
    demoted = False

    high_issues = [c for c in checks if c["severity"] == "high"]
    if high_issues:
        confidence = min(confidence, 0.5)
        if draft.get("decision") in {"hire", "no_hire"}:
            demoted = True
            decision["decision"] = "undecided"

    if any(c["issue"] == "contradictions" and c["severity"] == "high" for c in checks):
        confidence = max(0.0, confidence - 0.2)
        decision["flag_review"] = True

    if any(c["issue"] == "overconfidence" for c in checks):
        confidence = max(0.0, confidence - 0.1)
        decision["flag_review"] = True

    if any(c["issue"] == "missing_competency" and c["severity"] == "high" for c in checks):
        decision["flag_review"] = True

    decision["confidence"] = round(confidence, 2)
    decision["demoted_to_undecided"] = demoted
    decision["review"] = {
        "checks": checks,
        "confidence_before": original_confidence,
        "confidence_after": round(confidence, 2),
        "adjusted": confidence != original_confidence or demoted,
    }
    return decision


async def decision_review_node(state: dict) -> dict:
    """Draft → Self Review → Final wiring for the engine's finalization chain."""
    draft = state.get("hiring_decision") or {}
    if not draft:
        logger.warning("Decision review: no hiring_decision draft to review")
        return state

    checks = review_decision(draft, state)
    final = finalize_decision(draft, checks)
    return {**state, "hiring_decision": final, "decision_review": final.get("review")}
