import logging

from langgraph.graph import StateGraph

from app.graph.interview_state import InterviewState
from app.agents.reflection_engine import reflection_engine
from app.agents.action_router import route

logger = logging.getLogger(__name__)


def build_reflection_subgraph() -> StateGraph:
    workflow = StateGraph(InterviewState)

    workflow.add_node("reflection_engine", reflection_engine)
    workflow.add_node("route_action", _route_action_node)

    workflow.set_entry_point("reflection_engine")
    workflow.add_edge("reflection_engine", "route_action")
    workflow.add_edge("route_action", "__end__")

    return workflow.compile()


async def _route_action_node(state: InterviewState) -> InterviewState:
    routed = route(state)
    return {
        **state,
        "routed_action": routed,
    }
