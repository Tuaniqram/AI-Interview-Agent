"""V5 hiring-decision capability — turns synthesis + sufficiency signals into an
explicit decision. LLM-backed with a deterministic fallback so finalization
never fails on an LLM outage.

Fix 9: the final ``hiring_decision.decision`` is the deterministic 7-point
scale (see ``decision_engine``); the LLM stays as the *draft* (kept under
``llm_draft``) and the legacy ``hiring_recommendation.verdict`` is untouched.
"""
import logging

from app.core.interview_state import InterviewState
from app.agents.decision.decision_engine import (
    decide_hiring_decision,
    decision_next_steps,
)

logger = logging.getLogger(__name__)


def _decision_signals(state: InterviewState) -> dict:
    report = state.get("final_report") or {}
    rec = state.get("hiring_recommendation") or {}
    hypotheses = state.get("hypotheses") or []

    confirmed = sum(1 for h in hypotheses if h.get("status") == "confirmed")
    refuted = sum(1 for h in hypotheses if h.get("status") == "refuted")
    confirmed_ratio = confirmed / (confirmed + refuted + 1)

    contradictions = sum(
        1 for c in (state.get("contradictions") or [])
        if c.get("severity") in ("high", "medium")
    )

    return {
        "holistic_score": report.get("holistic_score"),
        "coverage_ratio": rec.get("coverage_ratio"),
        "confirmed_ratio": confirmed_ratio,
        "contradiction_count": contradictions,
        "difficulty_reached": state.get("difficulty_level"),
        "evidence_count": len(state.get("evidence_store") or []),
    }


async def hiring_decision_node(state: InterviewState) -> InterviewState:
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    report = state.get("final_report") or {}
    rec = state.get("hiring_recommendation") or {}
    summary = state.get("competency_summary") or {}
    evidence = state.get("evidence_store") or []

    # Fix 9: deterministic 7-point scale first — the LLM explains THIS result.
    signals = _decision_signals(state)
    mapped = decide_hiring_decision(**signals)

    try:
        llm_service = get_llm_service()
        prompt = load_prompt(
            "decision",
            "hiring_decision.md",
            job_role=state.get("job_role", "Unknown"),
            holistic_score=report.get("holistic_score", "N/A"),
            fit_assessment=report.get("fit_assessment", "unknown"),
            verdict=mapped["decision"],
            decision_score=mapped["decision_score"],
            decision_rationale=mapped["rationale"],
            decision_signals=", ".join(
                f"{k}={v}" for k, v in mapped["signals"].items()
            ),
            coverage_ratio=rec.get("coverage_ratio", "N/A"),
            evidence_summary=(
                f"{len(evidence)} evidence items across {len(summary)} competencies"
                if evidence
                else "no evidence collected"
            ),
            strengths=_join(report.get("key_strengths")),
            weaknesses=_join(report.get("key_weaknesses")),
            competency_summary=(
                ", ".join(
                    f"{comp} (avg {s.get('average_score', 0.0)}, "
                    f"{s.get('evidence_count', 0)} evidence)"
                    for comp, s in summary.items()
                )
                or "(none)"
            ),
        )
        response = await llm_service.invoke(prompt=prompt, temperature=0.2, max_tokens=300, tier="strong")
        from app.intelligence._helpers import parse_json

        data = parse_json(response)
        next_steps = data.get("next_steps", [])
        # The LLM explains the engine's decision — it never makes one. The
        # draft carries no ``decision``/``confidence`` so the report can never
        # show the LLM and the engine disagreeing.
        llm_draft = {
            "rationale": str(data.get("rationale", "")),
            "next_steps": next_steps if isinstance(next_steps, list) else [],
        }
    except Exception as e:
        logger.warning(f"Hiring decision LLM failed ({e}), using deterministic fallback")
        llm_draft = _decision_deterministic(report, mapped["decision"])

    # Deterministic confidence: distance of the decision score from the 5.0
    # midpoint, capped — never borrowed from the LLM.
    # D4: tempered by evidence of problems — flagged weaknesses, falsified
    # hypotheses and serious contradictions each shave it, so a report full of
    # "shallow analysis" findings can never carry a 0.9 confidence.
    hypotheses = state.get("hypotheses") or []
    falsified = sum(1 for h in hypotheses if h.get("status") == "refuted")
    weakness_penalty = min(
        0.25,
        0.05 * len(report.get("key_weaknesses") or [])
        + 0.05 * falsified
        + 0.10 * signals["contradiction_count"],
    )
    decision_confidence = round(
        min(
            0.9,
            max(
                0.5,
                0.5 + abs(mapped["decision_score"] - 5.0) / 10.0 - weakness_penalty,
            ),
        ),
        2,
    )

    return {
        **state,
        "hiring_decision": {
            "decision": mapped["decision"],
            "decision_score": mapped["decision_score"],
            "decision_scale": mapped["decision_scale"],
            "signals": mapped["signals"],
            "confidence": decision_confidence,
            "rationale": mapped["rationale"],
            "next_steps": decision_next_steps(mapped["decision"]),
            "llm_draft": llm_draft,
        },
    }


def _decision_deterministic(report: dict, verdict: str) -> dict:
    holistic = report.get("holistic_score")

    if verdict == "hire" and holistic is not None and float(holistic) >= 7.0:
        rationale = (
            f"Deterministic verdict '{verdict}' with holistic score {holistic} "
            f"— solid evidence across the required competencies."
        )
    elif verdict == "no_hire" or (holistic is not None and float(holistic) < 5.0):
        rationale = (
            f"Deterministic verdict '{verdict}' with holistic score {holistic} "
            f"— evidence does not meet the role's requirements."
        )
    else:
        rationale = (
            f"Deterministic verdict '{verdict}' from holistic score {holistic} "
            f"and coverage — further probing may be warranted."
        )

    return {
        "rationale": rationale,
        "next_steps": _next_steps(verdict),
    }


def _next_steps(decision: str) -> list[str]:
    if decision == "hire":
        return ["schedule follow-up with the hiring manager", "prepare offer discussion"]
    if decision == "no_hire":
        return ["archive candidate profile", "log feedback for interviewer calibration"]
    return ["schedule a short probe round", "compare against other shortlisted candidates"]


def _join(items: list) -> str:
    if not items:
        return "(none highlighted)"
    return ", ".join(str(item) for item in items)
