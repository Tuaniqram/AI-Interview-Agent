import logging
from langgraph.checkpoint.memory import MemorySaver
from app.graph.interview_state import InterviewState
from app.agents.session_init_node import session_init_node
from app.agents.phase_decision_node import phase_decision_node
from app.agents.company_context_node import department_context_node
from app.agents.question_generation_node import question_generation_node

logger = logging.getLogger(__name__)


def create_question_workflow():
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(InterviewState)
    
    workflow.add_node("session_init", session_init_node)
    workflow.add_node("phase_decision", phase_decision_node)
    workflow.add_node("department_context", department_context_node)
    workflow.add_node("question_generation", question_generation_node)
    
    workflow.set_entry_point("session_init")
    
    workflow.add_edge("session_init", "phase_decision")
    workflow.add_edge("phase_decision", "department_context")
    workflow.add_edge("department_context", "question_generation")
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