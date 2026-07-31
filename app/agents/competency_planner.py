import logging
from typing import Any

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


_PRIORITY_SCORE = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def plan_competencies(state: InterviewState) -> list[dict]:
    style = state.get("interview_style", {})
    evidence_summary = state.get("competency_summary", {})
    strategy = state.get("interview_strategy", {})
    strategy_priorities = strategy.get("competency_priority", {}) if strategy else {}
    taxonomy = state.get("competency_taxonomy") or COMPETENCY_TAXONOMY

    results = []
    for comp_def in taxonomy:
        comp_id = comp_def["id"]
        priority_str = (
            strategy_priorities.get(comp_id)
            or style.get("base_competency_priority", {}).get(comp_id)
            or "LOW"
        )
        priority_score = _PRIORITY_SCORE.get(priority_str, 1)

        min_evidence = (
            style.get("evidence_minimums", {}).get(comp_id)
            or comp_def.get("default_min_evidence", 2)
        )
        collected = evidence_summary.get(comp_id, {}).get("evidence_count", 0)
        avg_score = evidence_summary.get(comp_id, {}).get("average_score", 0.0)
        coverage = min(collected / min_evidence, 1.0) if min_evidence > 0 else 1.0
        gap = round(1.0 - coverage, 2)
        last_evidence_at = evidence_summary.get(comp_id, {}).get("last_evidence_at", "")

        results.append({
            "id": comp_id,
            "name": comp_def["name"],
            "category": comp_def["category"],
            "priority": priority_str,
            "priority_score": priority_score,
            "gap": gap,
            "coverage": round(coverage, 2),
            "evidence_count": collected,
            "evidence_required": min_evidence,
            "average_score": round(avg_score, 2),
            "dimension": comp_def["evidence_dimensions"][0],
            "dimensions": comp_def["evidence_dimensions"],
            "last_evidence_at": last_evidence_at,
        })

    results.sort(key=lambda c: (
        -c["priority_score"],
        -c["gap"],
        c["evidence_count"],
    ))

    return results


def get_next_competency(competencies: list[dict], current_id: str | None = None) -> dict | None:
    if not competencies:
        return None
    if current_id:
        for i, c in enumerate(competencies):
            if c["id"] == current_id:
                next_idx = i + 1
                if next_idx < len(competencies):
                    return competencies[next_idx]
    return competencies[0]


def get_high_priority_gaps(competencies: list[dict]) -> list[dict]:
    return [c for c in competencies if c["priority"] == "HIGH" and c["gap"] > 0.2]


def is_sufficient(
    competencies: list[dict],
    threshold: float = 0.85,
) -> bool:
    high_priority = [c for c in competencies if c["priority"] == "HIGH"]
    if not high_priority:
        return False
    return all(c["coverage"] >= threshold for c in high_priority)
