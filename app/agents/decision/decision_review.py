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
decisive verdicts to ``insufficient_evidence``, flag for human review). Pure
capability — no DB, no shared-state mutation.

Fix 9: decisive 7-point labels (strong_hire … strong_no_hire) demote exactly
like the legacy ``hire``/``no_hire``.
"""
import logging

from app.agents.decision.decision_engine import DECISIVE_DECISIONS

logger = logging.getLogger(__name__)

MIN_EVIDENCE_FOR_HIGH_CONFIDENCE = 4
MIN_AVG_STRENGTH_FOR_HIGH_CONFIDENCE = 0.6
MIN_COVERAGE_FOR_DECISION = 0.5
OVERCONFIDENCE_CONFIDENCE_FLOOR = 0.75
SUFFICIENCY_GAP_THRESHOLD = 0.3
REVIEW_SEVERITIES = ("low", "medium", "high")
HIRE_SIDE_DECISIONS = {"strong_hire", "hire", "lean_hire"}

__all__ = [
    "MIN_EVIDENCE_FOR_HIGH_CONFIDENCE",
    "MIN_AVG_STRENGTH_FOR_HIGH_CONFIDENCE",
    "MIN_COVERAGE_FOR_DECISION",
    "OVERCONFIDENCE_CONFIDENCE_FLOOR",
    "SUFFICIENCY_GAP_THRESHOLD",
    "review_decision",
    "finalize_decision",
    "compute_flag_review",
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

    # 5. Semantic evidence-reading checks (LLM-informed, capped at medium so they
    # can flag for review / trim confidence but never demote a decisive verdict).
    checks.extend(_semantic_checks(state))

    return sorted(
        checks,
        key=lambda c: -REVIEW_SEVERITIES.index(c["severity"]),
    )


def _semantic_checks(state: dict) -> list[dict]:
    from app.agents.reasoning.evidence_reading import evidence_reading_checks

    return evidence_reading_checks(state.get("evidence_reading"))


# Rules whose adjustments are about coverage of the role (a short or unbalanced interview), which on their own
# don't call for a human reviewer.
_COVERAGE_RULES = {"coverage", "review:missing_competency"}
FLAG_UNSUBSTANTIATED_SHARE = 0.3
FLAG_OFF_RUBRIC_COUNT = 3


def compute_flag_review(decision: dict, checks: list[dict] | None = None, state: dict | None = None) -> bool:
    """Plan step 7 (P11): ask for a human only on real findings. True when any of:

    * a demotion or cap other than coverage was applied (``decision["adjustments"]``)
    * >= 3 off-rubric red flags
    * any cross-answer risk from the final read
    * unsubstantiated share >= 0.3 (from the evaluator's answer signals)
    * any claim conflict that is not ``explained``
    """
    from app.agents.reasoning.evidence_engine import unsubstantiated_share

    checks = checks or []
    state = state or {}
    if any(
        isinstance(a, dict) and a.get("rule") not in _COVERAGE_RULES
        for a in decision.get("adjustments") or []
    ):
        return True
    for c in checks:
        if c.get("issue") == "off_rubric_flag" and int(c.get("count", 0) or 0) >= FLAG_OFF_RUBRIC_COUNT:
            return True
        if c.get("issue") == "cross_answer_risk":
            return True
    share = unsubstantiated_share(state.get("answer_signals"))
    if share is not None and share >= FLAG_UNSUBSTANTIATED_SHARE:
        return True
    return any(
        isinstance(c, dict) and c.get("status", "open") != "explained"
        for c in state.get("claim_conflicts") or []
    )


def finalize_decision(draft: dict, checks: list[dict], state: dict | None = None) -> dict:
    """Apply review findings to the draft, producing the final decision.

    Downgrades confidence for any finding, demotes a decisive verdict to
    ``undecided`` when evidence is insufficient, and attaches the review
    trail to the returned decision.
    """
    decision = dict(draft)
    # Plan step 3: every demotion is recorded with its reason, next to the decision engine's caps.
    adjustments = [dict(a) for a in (draft.get("adjustments") or []) if isinstance(a, dict)]
    original_confidence = float(draft.get("confidence", 0.0))
    confidence = original_confidence
    demoted = False

    high_issues = [c for c in checks if c["severity"] == "high"]
    if high_issues:
        confidence = min(confidence, 0.5)
        current = decision.get("decision")
        if current in DECISIVE_DECISIONS or current in {"hire", "no_hire"}:
            demoted = True
            decision["decision"] = "insufficient_evidence"
            adjustments.append({
                "rule": f"review:{high_issues[0]['issue']}",
                "from": current,
                "to": "insufficient_evidence",
                "reason": high_issues[0].get("detail") or high_issues[0]["issue"],
            })

    if any(c["issue"] == "contradictions" and c["severity"] == "high" for c in checks):
        confidence = max(0.0, confidence - 0.2)

    if any(c["issue"] == "overconfidence" for c in checks):
        confidence = max(0.0, confidence - 0.1)

    # Semantic (evidence-reading) findings trim a little confidence. Plan step 7: they never demote — the
    # reading is a secondary signal; changed figures are demoted by the claim ledger's deterministic caps.
    semantic_issues = [c for c in checks if c.get("issue") in ("off_rubric_flag", "cross_answer_risk")]
    if semantic_issues:
        confidence = max(0.0, confidence - 0.05 * min(len(semantic_issues), 2))

    decision["adjustments"] = adjustments
    # Compatibility: report builder and harness read ``demotion_reason`` — the first recorded adjustment.
    if adjustments and not decision.get("demotion_reason"):
        decision["demotion_reason"] = adjustments[0]["reason"]

    decision["confidence"] = round(confidence, 2)
    decision["demoted_to_undecided"] = demoted
    decision["flag_review"] = compute_flag_review(decision, checks, state)
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
    final = finalize_decision(draft, checks, state)
    return {**state, "hiring_decision": final, "decision_review": final.get("review")}
