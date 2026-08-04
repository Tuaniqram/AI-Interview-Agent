import logging

from langgraph.graph import StateGraph

from app.graph.interview_state import InterviewState
from app.agents.unified_evaluator_node import unified_evaluator_node
from app.agents.evidence_extractor_node import evidence_extractor_node

logger = logging.getLogger(__name__)


def build_evaluation_subgraph() -> StateGraph:
    workflow = StateGraph(InterviewState)

    workflow.add_node("unified_evaluator", unified_evaluator_node)
    workflow.add_node("evidence_extractor", evidence_extractor_node)

    workflow.set_entry_point("unified_evaluator")
    workflow.add_edge("unified_evaluator", "evidence_extractor")
    workflow.add_edge("evidence_extractor", "__end__")

    return workflow.compile()
