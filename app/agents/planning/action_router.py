from app.core.interview_state import InterviewState
from app.agents.reasoning.contradiction_engine import MIN_QUESTIONS_BEFORE_FINISH


def route_after_planner(state: InterviewState) -> str:
    """Route after the planner runs.

    Decides from the planner's output — not the stale ``hypothesis_target`` —
    so a rotation never hard-stops the interview while competencies remain
    uncovered (previously any null target ended the session). Falls back to a
    question even with an empty plan before the minimum question count, so the
    hypothesis node re-seeds rather than finalizing prematurely.
    """
    if state.get("planned_competency") or state.get("next_competency"):
        return "question_subgraph"
    if int(state.get("question_number", 0) or 0) < MIN_QUESTIONS_BEFORE_FINISH:
        return "question_subgraph"
    return "finish"
