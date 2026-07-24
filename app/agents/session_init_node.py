"""
Session Initialization Node - LangGraph Node Agent
Initializes the interview session state.
"""
import logging
from datetime import datetime
from typing import TypedDict
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


def session_init_node(state: InterviewState) -> InterviewState:
    """
    Initialize interview session state.
    
    Args:
        state: Current interview state
        
    Returns:
        Updated state with initialization data
    """
    logger.info(f"Initializing session: {state.get('session_id', 'new')}")
    
    # Initialize empty conversation history
    history = state.get('conversation_history', [])
    if not history:
        history = []
        logger.info("Created empty conversation history")
    
    # Get current phase, ensure it's valid
    current_phase = state.get('current_phase', 'intro')
    
    # Get question number
    question_number = state.get('question_number', 0)
    
    # Get interview flow type
    flow_type = state.get('flow_type', 'department')
    
    # Initialize RAG context
    department_context = state.get('department_context', [])
    
    # Initialize technical evaluation data
    technical_score = None
    communication_score = None
    strengths = []
    weaknesses = []
    
    # Record this node execution
    nodes = state.get('nodes_executed', ['session_init'])
    
    # Record start time if not set
    start_time = state.get('start_time')
    if not start_time:
        start_time = datetime.now()
    
    new_state: InterviewState = {
        **state,
        'conversation_history': history,
        'current_phase': current_phase,
        'question_number': question_number,
        'flow_type': flow_type,
        'department_context': department_context,
        'rag_metadata': state.get('rag_metadata', {}),
        'technical_score': technical_score,
        'communication_score': communication_score,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'nodes_executed': nodes + ['session_init'],
        'start_time': start_time
    }
    
    logger.info(f"Session initialized. Phase: {current_phase}")
    return new_state