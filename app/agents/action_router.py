from app.graph.interview_state import InterviewState


def route_after_planner(state: InterviewState) -> str:
    hypothesis_target = state.get("hypothesis_target")
    if hypothesis_target:
        return "question_subgraph"
    return "finish"
