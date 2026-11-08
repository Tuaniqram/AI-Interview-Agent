"""V5 hiring-decision capability — turns synthesis + sufficiency signals into an explicit decision.

Plan step 3:
- ``hiring_decision_node`` is deterministic only (``decision_engine.decide_hiring_decision``): the score, the
  label, every cap and the next steps are computed in code.
- ``explain_final_decision`` runs LAST in finalization — after the decision review and the calibration
  override — and asks the LLM to explain the FINAL decision (including every adjustment), storing it under
  ``llm_draft.rationale``. On an LLM failure a deterministic explanation is used. The LLM never decides.
"""
import logging

from app.core.interview_state import InterviewState
from app.agents.decision.decision_engine import (
    decide_hiring_decision,
    decision_next_steps,
)

logger = logging.getLogger(__name__)


def _decision_signals(state: InterviewState) -> dict:
    from app.agents.planning.difficulty_engine import max_difficulty_reached, role_difficulty_floor
    from app.agents.reasoning.contradiction_engine import (
        average_evidence_confidence,
        canonical_score_from_state,
        resolved_hypothesis_confidence,
    )
    from app.agents.reasoning.evidence_engine import unsubstantiated_share

    report = state.get("final_report") or {}
    rec = state.get("hiring_recommendation") or {}
    hypotheses = state.get("hypotheses") or []

    # N4: one "confirmed ratio" — the same resolved-hypothesis confidence the sufficiency layer uses.
    statuses = [h.get("status") for h in hypotheses]
    confirmed_ratio = resolved_hypothesis_confidence(
        statuses.count("confirmed"),
        statuses.count("refuted"),
        statuses.count("untested"),
        average_evidence_confidence(state.get("competency_summary") or {}) or 0.5,
    )

    # Plan step 5: the score penalty counts serious NON-claim contradictions (score inconsistencies);
    # claim conflicts act through cap 7 only, so they are never counted twice.
    contradictions = sum(
        1 for c in (state.get("contradictions") or [])
        if c.get("severity") in ("high", "medium") and c.get("type") != "claim_conflict"
    )
    from app.agents.reasoning.claim_ledger import unresolved_conflicts

    claim_conflicts = state.get("claim_conflicts") or []
    open_conflicts = unresolved_conflicts(claim_conflicts)

    holistic = report.get("holistic_score")
    if holistic is None:
        holistic = canonical_score_from_state(state)

    return {
        "holistic_score": holistic,
        "coverage_ratio": rec.get("coverage_ratio"),
        "confirmed_ratio": confirmed_ratio,
        "contradiction_count": contradictions,
        "difficulty_reached": max_difficulty_reached(state),
        "evidence_count": len(state.get("evidence_store") or []),
        "role_floor": role_difficulty_floor(state.get("job_role", "")),
        "unsubstantiated_share": unsubstantiated_share(state.get("answer_signals")),
        "unexplained_claim_conflicts": len(open_conflicts),
        "inflation_admitted": any(c.get("kind") == "inflation_admitted" for c in open_conflicts),
        # Cap 7b counts the changed figures themselves, explained or not; an admitted inflation is its own cap.
        "claim_conflicts_total": sum(1 for c in claim_conflicts if c.get("kind") != "inflation_admitted"),
    }


def _decision_confidence(state: InterviewState, decision_score: float, contradiction_count: int) -> float:
    """Deterministic confidence: distance of the score from the 5.0 midpoint, capped.

    D4: tempered by evidence of problems — flagged weaknesses, falsified hypotheses and serious
    contradictions each shave it, so a report full of "shallow analysis" findings can never carry 0.9.
    """
    report = state.get("final_report") or {}
    falsified = sum(1 for h in (state.get("hypotheses") or []) if h.get("status") == "refuted")
    weakness_penalty = min(
        0.25,
        0.05 * len(report.get("key_weaknesses") or [])
        + 0.05 * falsified
        + 0.10 * contradiction_count,
    )
    return round(min(0.9, max(0.5, 0.5 + abs(decision_score - 5.0) / 10.0 - weakness_penalty)), 2)


async def hiring_decision_node(state: InterviewState) -> InterviewState:
    """The deterministic decision (no LLM): score -> label -> ordered caps, all recorded."""
    signals = _decision_signals(state)
    mapped = decide_hiring_decision(**signals)
    return {
        **state,
        "hiring_decision": {
            "decision": mapped["decision"],
            "draft_decision": mapped["draft_decision"],
            "decision_score": mapped["decision_score"],
            "decision_scale": mapped["decision_scale"],
            "signals": mapped["signals"],
            "adjustments": list(mapped["adjustments"]),
            "flag_review": mapped["flag_review"],
            "confidence": _decision_confidence(state, mapped["decision_score"], signals["contradiction_count"]),
            "rationale": mapped["rationale"],
            "next_steps": decision_next_steps(mapped["decision"]),
        },
    }


def _adjustments_text(adjustments: list) -> str:
    lines = [
        f"  - {a.get('rule')}: {a.get('from')} -> {a.get('to')} ({a.get('reason')})"
        for a in adjustments or []
        if isinstance(a, dict)
    ]
    return "\n".join(lines) or "  None"


async def explain_final_decision(state: InterviewState) -> InterviewState:
    """Explain the FINAL decision in plain language (PROMPTS.md section 6); never changes it."""
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    decision = dict(state.get("hiring_decision") or {})
    if not decision:
        return state
    report = state.get("final_report") or {}
    rec = state.get("hiring_recommendation") or {}
    summary = state.get("competency_summary") or {}
    evidence = state.get("evidence_store") or []
    final = decision.get("decision") or "insufficient_evidence"

    try:
        prompt = load_prompt(
            "decision",
            "hiring_decision.md",
            job_role=state.get("job_role", "Unknown"),
            verdict=final,
            draft_verdict=decision.get("draft_decision") or final,
            decision_score=decision.get("decision_score", "N/A"),
            decision_rationale=decision.get("rationale", ""),
            decision_signals=", ".join(f"{k}={v}" for k, v in (decision.get("signals") or {}).items()),
            adjustments=_adjustments_text(decision.get("adjustments")),
            holistic_score=report.get("holistic_score", "N/A"),
            coverage_ratio=rec.get("coverage_ratio", "N/A"),
            evidence_summary=(
                f"{len(evidence)} evidence items across {len(summary)} competencies"
                if evidence
                else "no evidence collected"
            ),
            fit_assessment=report.get("fit_assessment", "unknown"),
            strengths=_join(report.get("key_strengths")),
            weaknesses=_join(report.get("key_weaknesses")),
            competency_summary=(
                ", ".join(
                    f"{comp} (avg {s.get('average_score', 0.0)}, {s.get('evidence_count', 0)} evidence)"
                    for comp, s in summary.items()
                )
                or "(none)"
            ),
            next_steps="; ".join(decision.get("next_steps") or decision_next_steps(final)),
        )
        response = await get_llm_service().invoke(prompt=prompt, temperature=0.2, max_tokens=300, tier="strong")
        from app.intelligence._helpers import parse_json

        data = parse_json(response)
        rationale = str((data or {}).get("rationale", "") or "").strip()
        if not rationale:
            raise ValueError("empty rationale")
        llm_draft = {"rationale": rationale}
    except Exception as e:  # noqa: BLE001 - the explanation is optional, the decision is not
        logger.warning(f"Hiring decision explanation LLM failed ({e}), using deterministic text")
        llm_draft = _decision_deterministic(report, final, decision.get("adjustments"))

    decision["llm_draft"] = llm_draft
    return {**state, "hiring_decision": decision}


def _decision_deterministic(report: dict, verdict: str, adjustments: list | None = None) -> dict:
    holistic = report.get("holistic_score")

    if verdict in ("strong_hire", "hire") and holistic is not None and float(holistic) >= 7.0:
        rationale = (
            f"Deterministic verdict '{verdict}' with holistic score {holistic} "
            f"— solid evidence across the required competencies."
        )
    elif verdict in ("no_hire", "strong_no_hire") or (holistic is not None and float(holistic) < 5.0):
        rationale = (
            f"Deterministic verdict '{verdict}' with holistic score {holistic} "
            f"— evidence does not meet the role's requirements."
        )
    else:
        rationale = (
            f"Deterministic verdict '{verdict}' from holistic score {holistic} "
            f"and coverage — further probing may be warranted."
        )
    reasons = [a.get("reason") for a in adjustments or [] if isinstance(a, dict) and a.get("reason")]
    if reasons:
        rationale += " Adjusted: " + "; ".join(reasons) + "."

    return {
        "rationale": rationale,
        "next_steps": decision_next_steps(verdict),
    }


def _join(items: list) -> str:
    if not items:
        return "(none highlighted)"
    return ", ".join(str(item) for item in items)
