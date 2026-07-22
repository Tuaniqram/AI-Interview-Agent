"""
Answer Evaluation LangGraph Workflow
Workflow for evaluating candidate answer.
"""
import logging
from langgraph.checkpoint.memory import MemorySaver
from app.graph.interview_state import InterviewState
from app.agents.answer_evaluator_node import answer_evaluator_node
from app.agents.interview_flow_node import interview_flow_node
from app.agents.decision_node import decision_node

logger = logging.getLogger(__name__)


def create_evaluation_workflow():
    """
    Create the answer evaluation LangGraph workflow.
    
    Flow:
    1. Answer Evaluation → Score candidate answer and provide feedback
    2. Interview Flow → Determine next phase/difficulty based on performance
    3. Decision → Determine next action (continue/finish) - rule-based safety net
    
    Returns:
        Compiled StateGraph workflow
    """
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(InterviewState)
    
    # Add nodes
    workflow.add_node("answer_evaluator", answer_evaluator_node)
    workflow.add_node("interview_flow", interview_flow_node)
    workflow.add_node("decision", decision_node)
    
    # Set entry point
    workflow.set_entry_point("answer_evaluator")
    
    # Add edges (deterministic flows)
    workflow.add_edge("answer_evaluator", "interview_flow")
    workflow.add_edge("interview_flow", "decision")
    workflow.add_edge("decision", END)
    
    # Compile the workflow
    checkpointer = MemorySaver()
    evaluation_workflow = workflow.compile(checkpointer=checkpointer)
    
    logger.info("Answer Evaluation LangGraph workflow compiled successfully")
    
    return evaluation_workflow


# Create singleton instance
_evaluation_workflow = None


def get_evaluation_workflow():
    """
    Get or create the evaluation workflow singleton.
    
    Returns:
        Compiled StateGraph workflow
    """
    global _evaluation_workflow
    
    if _evaluation_workflow is None:
        _evaluation_workflow = create_evaluation_workflow()
    
    return _evaluation_workflow