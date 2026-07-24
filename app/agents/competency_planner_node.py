import logging

from app.graph.interview_state import InterviewState
from app.agents.competency_planner import (
    plan_competencies,
    get_next_competency,
    is_sufficient,
    get_high_priority_gaps,
)

logger = logging.getLogger(__name__)


async def competency_planner_node(state: InterviewState) -> InterviewState:
    plan = plan_competencies(state)

    existing_id = (state.get("competency_plan") or [{}])[0].get("id") if state.get("competency_plan") else None
    next_comp = get_next_competency(plan, existing_id)
    gaps = get_high_priority_gaps(plan)
    sufficient = is_sufficient(plan)

    return {
        **state,
        "competency_plan": plan,
        "next_competency": next_comp,
        "competency_gaps": gaps,
        "evidence_sufficiency": {
            "is_sufficient": sufficient,
            "remaining_gaps": len(gaps),
        },
    }
