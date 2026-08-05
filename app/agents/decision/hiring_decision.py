"""V5 hiring-decision capability — turns synthesis + sufficiency signals into an
explicit decision. LLM-backed with a deterministic fallback so finalization
never fails on an LLM outage.
"""
import json
import logging

from app.core.interview_state import InterviewState

logger = logging.getLogger(__name__)


async def hiring_decision_node(state: InterviewState) -> InterviewState:
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    report = state.get("final_report") or {}
    rec = state.get("hiring_recommendation") or {}
    summary = state.get("competency_summary") or {}
    evidence = state.get("evidence_store") or []

    try:
        llm_service = get_llm_service()
        prompt = load_prompt(
            "decision",
            "hiring_decision.md",
            job_role=state.get("job_role", "Unknown"),
            holistic_score=report.get("holistic_score", "N/A"),
            fit_assessment=report.get("fit_assessment", "unknown"),
            verdict=rec.get("verdict", "insufficient_evidence"),
            verdict_confidence=rec.get("confidence", 0.0),
            coverage_ratio=rec.get("coverage_ratio", "N/A"),
            evidence_summary=(
                f"{len(evidence)} evidence items across {len(summary)} competencies"
                if evidence
                else "no evidence collected"
            ),
            strengths=_join(report.get("key_strengths")),
            weaknesses=_join(report.get("key_weaknesses")),
        )
        response = await llm_service.invoke(prompt=prompt, temperature=0.2, max_tokens=300, tier="strong")
        data = json.loads(response.strip().lstrip("```json").rstrip("```").strip())
        next_steps = data.get("next_steps", [])
        decision = {
            "decision": str(data.get("decision", "undecided")),
            "confidence": round(float(data.get("confidence", 0.0)), 2),
            "rationale": str(data.get("rationale", "")),
            "next_steps": next_steps if isinstance(next_steps, list) else [],
        }
    except Exception as e:
        logger.warning(f"Hiring decision LLM failed ({e}), using deterministic fallback")
        decision = _decision_deterministic(report, rec)

    return {**state, "hiring_decision": decision}


def _decision_deterministic(report: dict, rec: dict) -> dict:
    verdict = rec.get("verdict", "insufficient_evidence")
    holistic = report.get("holistic_score")

    if verdict == "hire" and holistic is not None and float(holistic) >= 7.0:
        decision, confidence = "hire", 0.8
    elif verdict == "no_hire" or (holistic is not None and float(holistic) < 5.0):
        decision, confidence = "no_hire", 0.7
    else:
        decision, confidence = "undecided", 0.5

    return {
        "decision": decision,
        "confidence": confidence,
        "rationale": (
            f"Deterministic decision from verdict '{verdict}' "
            f"and holistic score {holistic}."
        ),
        "next_steps": _next_steps(decision),
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
