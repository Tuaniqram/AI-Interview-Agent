import logging
from datetime import datetime, timezone

from langgraph.graph import StateGraph

from app.graph.interview_state import InterviewState
from app.agents.question_generator_node import question_generator_node

logger = logging.getLogger(__name__)


def build_question_subgraph() -> StateGraph:
    workflow = StateGraph(InterviewState)

    workflow.add_node("generate_question", question_generator_node)
    workflow.add_node("wait_for_answer", _wait_for_answer_node)
    workflow.add_node("check_answer", _check_answer_node)

    workflow.set_entry_point("generate_question")
    workflow.add_edge("generate_question", "wait_for_answer")
    workflow.add_conditional_edges(
        "wait_for_answer",
        _route_after_answer,
        {"evaluate": "check_answer", "retry": "generate_question", "skip": "generate_question"},
    )
    workflow.add_edge("check_answer", "__end__")

    return workflow.compile()


async def _wait_for_answer_node(state: InterviewState) -> InterviewState:
    return {
        **state,
        "answer_received_at": datetime.now(timezone.utc).isoformat(),
    }


async def _check_answer_node(state: InterviewState) -> InterviewState:
    answer = state.get("candidate_answer", "")
    if not answer or not answer.strip():
        return {
            **state,
            "skip_evaluation": True,
        }
    return state


def _route_after_answer(state: InterviewState) -> str:
    answer = state.get("candidate_answer", "")
    if not answer or not answer.strip():
        question_number = state.get("question_number", 0)
        if question_number > 3:
            return "skip"
        return "retry"
    return "evaluate"
