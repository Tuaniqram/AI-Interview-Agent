"""
Internal Interview Agent LangGraph Workflow
Provided for backward compatibility. New code should use question_workflow and evaluation_workflow.
"""
import logging
from app.graph.interview_state import InterviewState
from app.agents.session_init_node import session_init_node
from app.agents.company_context_node import company_context_node
from app.agents.question_generation_node import question_generation_node
from app.agents.answer_evaluator_node import answer_evaluator_node
from app.agents.decision_node import decision_node

logger = logging.getLogger(__name__)


def create_interview_workflow():
    """
    Create and configure the complete Interview Agent LangGraph workflow.
    
    Flow:
    1. Session Init → Initialize state
    2. Company Context → Retrieve company documents
    3. Question Generation → Get AI-generated question
    4. Answer Evaluation → Score candidate answer
    5. Decision → Determine next action
    6. Loop back if not finished
    
    Returns:
        Compiled StateGraph workflow
    """
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(InterviewState)
    
    # Add nodes
    workflow.add_node("session_init", session_init_node)
    workflow.add_node("company_context", company_context_node)
    workflow.add_node("question_generation", question_generation_node)
    workflow.add_node("answer_evaluation", answer_evaluator_node)
    workflow.add_node("decision", decision_node)
    
    # Set entry point
    workflow.set_entry_point("session_init")
    
    # Add edges (deterministic flows)
    # After session init → always go to company context
    workflow.add_edge("session_init", "company_context")
    
    # After company context → always go to question generation
    workflow.add_edge("company_context", "question_generation")
    
    # After question generation → check if completed, then go to decision
    # This prevents unnecessary loops
    workflow.add_conditional_edges(
        "question_generation",
        should_transition_finish,
        {
            "finish": END,
            "continue": "answer_evaluation",
        }
    )
    
    # After answer evaluation → always go to decision
    workflow.add_edge("answer_evaluation", "decision")
    
    # After decision → check if finished or continue with next question
    workflow.add_conditional_edges(
        "decision",
        should_continue,
        {
            "finish": END,
            "continue": "question_generation",
        }
    )
    
    # Compile the workflow
    interview_agency = workflow.compile()
    
    logger.info("Interview Agent LangGraph workflow compiled successfully (internal use only)")
    
    return interview_agency


def should_transition_finish(state: InterviewState) -> str:
    """
    Determine if question generation should finish or proceed to evaluation.
    
    This check helps prevent infinite loops by detecting when generation is complete.
    
    Args:
        state: Current interview state
        
    Returns:
        "finish" or "continue"
    """
    # If next_action is 'finish', end the workflow
    if state.get("next_action") == "finish":
        logger.info("Transitioning to finish from question_generation")
        return "finish"
    
    return "continue"


def should_continue(state: InterviewState) -> str:
    """
    Determine if interview should continue or finish.
    
    Args:
        state: Current interview state
        
    Returns:
        "continue" or "finish"
    """
    # Check if interview is marked as complete
    is_complete = state.get('is_complete', False)
    final_report = state.get('final_report')
    
    # If final report exists, interview is complete
    if final_report:
        logger.info(f"Interview complete: Final score={final_report.get('final_score')}")
        return "finish"
    
    # Use decision node's guidance
    next_action = state.get('next_action', 'continue')
    
    # If decision says finish and in conclusion phase, end it
    if next_action == 'finish' and state.get('current_phase') == 'conclusion':
        return "finish"
    
    # Default to continue unless explicitly told to finish
    return "continue"


# Create singleton instance
_interview_workflow = None


def get_interview_workflow():
    """
    Get or create the interview workflow singleton (deprecated).
    
    This is for backward compatibility only. New code should use get_question_workflow() and get_evaluation_workflow().
    
    Returns:
        Compiled StateGraph workflow
    """
    logger.warning("Using deprecated get_interview_workflow(). Please use get_question_workflow() and get_evaluation_workflow() instead.")
    
    global _interview_workflow
    
    if _interview_workflow is None:
        _interview_workflow = create_interview_workflow()
    
    return _interview_workflow