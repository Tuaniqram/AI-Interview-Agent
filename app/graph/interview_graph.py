import logging
from typing import Literal

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.graph.interview_state import InterviewState
from app.graph.subgraphs.question_subgraph import build_question_subgraph
from app.graph.subgraphs.evaluation_subgraph import build_evaluation_subgraph
from app.graph.subgraphs.reflection_subgraph import build_reflection_subgraph
from app.agents.session_init_node import session_init_node
from app.agents.company_context_node import department_context_node
from app.agents.candidate_profile_node import candidate_profile_node
from app.agents.competency_planner_node import competency_planner_node
from app.agents.strategy_brain_node import strategy_brain_node
from app.agents.hypothesis_node import hypothesis_node
from app.agents.synthesis_node import synthesis_node

logger = logging.getLogger(__name__)


def build_interview_graph() -> StateGraph:
    workflow = StateGraph(InterviewState)

    question_subgraph = build_question_subgraph()
    evaluation_subgraph = build_evaluation_subgraph()
    reflection_subgraph = build_reflection_subgraph()

    workflow.add_node("session_init", session_init_node)
    workflow.add_node("department_context", department_context_node)
    workflow.add_node("candidate_profile", candidate_profile_node)
    workflow.add_node("competency_planner", competency_planner_node)
    workflow.add_node("strategy_brain", strategy_brain_node)
    workflow.add_node("hypothesis_manager", hypothesis_node)
    workflow.add_node("question_subgraph", question_subgraph)
    workflow.add_node("evaluation_subgraph", evaluation_subgraph)
    workflow.add_node("reflection_subgraph", reflection_subgraph)
    workflow.add_node("synthesis", synthesis_node)

    workflow.set_entry_point("session_init")

    workflow.add_edge("session_init", "department_context")
    workflow.add_edge("department_context", "candidate_profile")
    workflow.add_edge("candidate_profile", "competency_planner")
    workflow.add_edge("competency_planner", "strategy_brain")
    workflow.add_edge("strategy_brain", "hypothesis_manager")
    workflow.add_edge("hypothesis_manager", "question_subgraph")
    workflow.add_edge("question_subgraph", "evaluation_subgraph")
    workflow.add_edge("evaluation_subgraph", "reflection_subgraph")

    workflow.add_conditional_edges(
        "reflection_subgraph",
        _route_interview_cycle,
        {
            "probe": "hypothesis_manager",
            "change_competency": "competency_planner",
            "finish": "synthesis",
        },
    )

    workflow.add_edge("synthesis", "__end__")

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


def _route_interview_cycle(state: InterviewState) -> Literal["probe", "change_competency", "finish"]:
    action = state.get("reflection_action", "probe")
    question_number = state.get("question_number", 0)
    max_questions = state.get("max_questions", 20)

    if question_number >= max_questions:
        return "finish"

    if action not in ("probe", "change_competency", "finish"):
        return "probe"

    return action
