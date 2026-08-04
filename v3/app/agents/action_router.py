import logging

from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


def route(state: InterviewState) -> str:
    raw = state.get("reflection_action", "")
    if isinstance(raw, dict):
        action = raw.get("action", "probe")
    elif isinstance(raw, str):
        action = raw
    else:
        action = "probe"

    logger.info(f"Action router: {action}")

    route_map = {
        "probe": "question_subgraph",
        "change_competency": "competency_planner",
        "increase_difficulty": "competency_planner",
        "finish": "synthesis",
    }

    return route_map.get(action, "question_subgraph")


def route_after_planner(state: InterviewState) -> str:
    hypothesis_target = state.get("hypothesis_target")
    if hypothesis_target:
        return "question_subgraph"
    return "finish"
