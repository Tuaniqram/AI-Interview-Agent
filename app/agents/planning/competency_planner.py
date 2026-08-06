import logging
from typing import Any

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.agents.reasoning.contradiction_engine import (
    MAX_QUESTIONS_PER_COMPETENCY,
    competency_question_counts,
)
from app.core.interview_state import InterviewState

logger = logging.getLogger(__name__)


_PRIORITY_SCORE = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}


def plan_competencies(state: InterviewState) -> list[dict]:
    style = state.get("interview_style", {})
    evidence_summary = state.get("competency_summary", {})
    strategy = state.get("interview_strategy", {})
    strategy_priorities = strategy.get("competency_priority", {}) if strategy else {}
    taxonomy = state.get("competency_taxonomy") or COMPETENCY_TAXONOMY

    # Fix 6: rotate only within the required (HIGH/MEDIUM, capped) set when the
    # session defined one, so LOW-priority competencies never consume budget.
    required = state.get("required_competencies") or []
    if required:
        focused = [c for c in taxonomy if c["id"] in required]
        if focused:
            taxonomy = focused

    question_counts = competency_question_counts(state.get("questions_asked", []))

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
        avg_confidence = evidence_summary.get(comp_id, {}).get("average_confidence", 0.0)
        coverage = min(collected / min_evidence, 1.0) if min_evidence > 0 else 1.0
        gap = round(1.0 - coverage, 2)
        last_evidence_at = evidence_summary.get(comp_id, {}).get("last_evidence_at", "")
        questions_count = question_counts.get(comp_id, 0)

        # unanswered hypotheses for this competency
        unanswered = 0
        for h in (state.get("hypotheses") or []):
            if h.get("competency") == comp_id and h.get("status") in ("untested", "testing"):
                unanswered += 1

        # proven means minimum evidence and small gap and decent confidence
        proven = (
            collected >= min_evidence and gap <= 0.2 and (avg_confidence or 0.0) >= 0.65
        )

        # difficulty progression: if candidate shows high avg_score and we have enough
        # evidence, surface this competency for harder probing (prefer escalation)
        difficulty_boost = 1 if (avg_score >= 8.0 and collected >= min_evidence) else 0

        # Fix for coverage: track if competency has no evidence yet to prioritize exploration
        # A competency is "uncovered" if it has 0 evidence collected (new exploration opportunity)
        is_uncovered = (collected == 0)

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
            "average_confidence": round(avg_confidence, 2),
            "is_uncovered": is_uncovered,
            "proven": proven,
            "dimension": comp_def["evidence_dimensions"][0],
            "dimensions": comp_def["evidence_dimensions"],
            "last_evidence_at": last_evidence_at,
            "questions_count": questions_count,
            "capped": questions_count >= MAX_QUESTIONS_PER_COMPETENCY,
            "unanswered_hypotheses": unanswered,
            "proven": proven,
            "difficulty_boost": difficulty_boost,
        })

    # Sorting prioritizes: priority, largest gap (weak competency), unanswered hypotheses,
    # uncovered status (to prioritize exploring new competencies), difficulty progression boost, then lowest evidence_count
    results.sort(key=lambda c: (
        -c["priority_score"],
        -c["gap"],
        -c["unanswered_hypotheses"],
        # Fix: prioritize uncovered competencies (0 comes first) to ensure exploration
        c["is_uncovered"],
        -c["difficulty_boost"],
        c["evidence_count"],
    ))

    return results


def get_next_competency(
    competencies: list[dict],
    current_id: str | None = None,
    max_questions_per_competency: int = MAX_QUESTIONS_PER_COMPETENCY,
) -> dict | None:
    """Next competency to probe, skipping any that hit the per-competency
    question cap (Fix 7) so rotation never re-asks a saturated area."""
    if not competencies:
        return None

    def _available():
        return [
            c for c in competencies
            if c.get("questions_count", 0) < max_questions_per_competency
        ]

    available = _available()
    if not available:
        return None

    if current_id:
        for i, c in enumerate(competencies):
            if c["id"] == current_id:
                for candidate in competencies[i + 1:]:
                    if candidate.get("questions_count", 0) < max_questions_per_competency:
                        return candidate
                break
    return available[0]


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


async def competency_planner_node(state: InterviewState) -> InterviewState:
    plan = plan_competencies(state)

    # Determine the currently-active competency id from authoritative sources:
    # 1) the planner's last committed planned_competency (preferred),
    # 2) the stored next_competency id, or
    # 3) the competency of the most recently asked question (questions_asked[-1]).
    # This avoids using the plan's first element which is not the runtime active
    # competency and caused repeated selection of the same competency.
    existing_id = None
    existing_id = state.get("planned_competency") or existing_id
    if not existing_id:
        next_c = state.get("next_competency") or {}
        existing_id = next_c.get("id") if isinstance(next_c, dict) else existing_id
    if not existing_id:
        q_asked = state.get("questions_asked") or []
        if q_asked:
            try:
                existing_id = q_asked[-1].get("competency")
            except Exception:
                existing_id = existing_id

    next_comp = get_next_competency(plan, existing_id)
    gaps = get_high_priority_gaps(plan)
    sufficient = is_sufficient(plan)

    return {
        **state,
        "competency_plan": plan,
        "next_competency": next_comp,
        "planned_competency": next_comp["id"] if next_comp else None,
        "competency_gaps": gaps,
        # Fix 11: the planner's HIGH-priority-only check no longer overwrites
        # ``evidence_sufficiency`` (the weighted evaluate_sufficiency from the
        # reflection drives the director's FINISH). Kept under its own key so
        # it stays observable without hijacking the finish decision.
        "planner_sufficient": sufficient,
    }
