"""Candidate Memory V5 — long-term candidate intelligence.

A candidate interviewed last month about database design is easier to assess
today. The memory layer keeps a compact learning record (proven strengths,
weaknesses, risk signals) inside the candidate brain and merges prior memory
into fresh builds so the next interview starts from history instead of zero.

Deterministic; persistence rides the existing candidate-brain snapshot tables.
"""
import logging

logger = logging.getLogger(__name__)


def build_candidate_memory(
    *,
    candidate_id: str = "",
    candidate_brain: dict | None = None,
    candidate_assessment: dict | None = None,
    prior_memory: dict | None = None,
) -> dict:
    """Compact memory snapshot for this interview round."""
    brain = candidate_brain or {}
    assessment = candidate_assessment or {}
    prior = prior_memory or {}
    history = list(prior.get("history") or [])

    round_record = {
        "role": brain.get("job_role") or "",
        "strengths": list(brain.get("strengths") or []),
        "weaknesses": list(brain.get("weaknesses") or []),
        "risk_signals": list(assessment.get("risk_signals") or []),
        "gap_areas": list(assessment.get("gap_areas") or []),
    }
    history.append(round_record)
    history = history[-5:]

    return {
        "candidate_id": candidate_id,
        "history": history,
        "learned_strengths": _consolidate(history, "strengths"),
        "learned_weaknesses": _consolidate(history, "weaknesses"),
        "learned_risk_signals": _consolidate(history, "risk_signals"),
        "interview_count": len(history),
    }


def _consolidate(history: list[dict], key: str) -> list[str]:
    seen: list[str] = []
    for record in history:
        for item in record.get(key) or []:
            if item and item not in seen:
                seen.append(item)
    return seen[:12]


def memory_into_candidate_brain(candidate_brain: dict, memory: dict) -> dict:
    """Attach the memory snapshot to the candidate brain for persistence."""
    brain = dict(candidate_brain or {})
    brain["candidate_memory"] = memory
    return brain


def merge_prior_memory(
    candidate_brain: dict | None,
    prior_brain: dict | None,
) -> dict:
    """Carry a previous round's memory (e.g. from a candidate_brains row)."""
    prior = (prior_brain or {}).get("candidate_memory") or {}
    if not prior:
        return candidate_brain or {}
    brain = dict(candidate_brain or {})
    brain["candidate_memory"] = prior
    return brain