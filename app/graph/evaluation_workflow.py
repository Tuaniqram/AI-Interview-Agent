"""
Answer Evaluation LangGraph Workflow
Workflow for evaluating candidate answer.
"""
import logging
from app.graph.interview_state import InterviewState
from app.agents.answer_evaluator_node import answer_evaluator_node
from app.agents.decision_node import decision_node

logger = logging.getLogger(__name__)


def create_evaluation_workflow():
    """
    Create the answer evaluation LangGraph workflow.
    
    Flow:
    1. Answer Evaluation → Score candidate answer and provide feedback
    2. Decision → Determine next action (continue/finish)
    3. END (STOP HERE - no more questions)
    
    Returns:
        Compiled StateGraph workflow
    """
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(InterviewState)
    
    # Add nodes
    workflow.add_node("answer_evaluator", answer_evaluator_node)
    workflow.add_node("decision", decision_node)
    
    # Set entry point
    workflow.set_entry_point("answer_evaluator")
    
    # Add edges (deterministic flows)
    # After answer evaluation → always go to decision
    workflow.add_edge("answer_evaluator", "decision")
    
    # After decision → END (stop here)
    workflow.add_edge("decision", END)
    
    # Compile the workflow
    evaluation_workflow = workflow.compile()
    
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