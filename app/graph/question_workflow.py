"""
Question Generation LangGraph Workflow
Workflow for generating exactly ONE interview question.
"""
import logging
from langgraph.checkpoint.memory import MemorySaver
from app.graph.interview_state import InterviewState
from app.agents.session_init_node import session_init_node
from app.agents.company_context_node import company_context_node
from app.agents.question_generation_node import question_generation_node

logger = logging.getLogger(__name__)


def create_question_workflow():
    """
    Create the question generation LangGraph workflow.
    
    Flow:
    1. Session Init → Initialize state
    2. Company Context → Retrieve company documents
    3. Question Generation → Get AI-generated question
    4. END (STOP HERE - no evaluation or decision)
    
    Returns:
        Compiled StateGraph workflow
    """
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(InterviewState)
    
    # Add nodes
    workflow.add_node("session_init", session_init_node)
    workflow.add_node("company_context", company_context_node)
    workflow.add_node("question_generation", question_generation_node)
    
    # Set entry point
    workflow.set_entry_point("session_init")
    
    # Add edges (deterministic flows)
    # After session init → always go to company context
    workflow.add_edge("session_init", "company_context")
    
    # After company context → always go to question generation
    workflow.add_edge("company_context", "question_generation")
    
    # After question generation → END (stop here)
    workflow.add_edge("question_generation", END)
    
    # Compile the workflow
    checkpointer = MemorySaver()
    question_workflow = workflow.compile(checkpointer=checkpointer)
    
    logger.info("Question Generation LangGraph workflow compiled successfully")
    
    return question_workflow


# Create singleton instance
_question_workflow = None


def get_question_workflow():
    """
    Get or create the question generation workflow singleton.
    
    Returns:
        Compiled StateGraph workflow
    """
    global _question_workflow
    
    if _question_workflow is None:
        _question_workflow = create_question_workflow()
    
    return _question_workflow