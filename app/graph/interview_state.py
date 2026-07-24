"""
State definition for the AI Interview Agent LangGraph workflow.
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class InterviewState(TypedDict, total=False):
    """State object for the AI Interview Agent workflow."""
    
    # Session Metadata
    session_id: str
    department_id: int
    candidate_id: str
    
    # Interview Context
    job_role: str
    flow_type: str  # "department", "skill", "adaptive"
    
    # Conversation State
    conversation_history: List[Dict[str, str]]
    current_phase: str  # "intro", "experience", "technical", "behavioral", "conclusion"
    phase_stage: int  # Progress within phase (0-10)
    
    # Question Management
    question_number: int
    total_questions: int
    current_question: str
    difficulty_level: int  # 1=Easy, 2=Medium, 3=Hard
    
    # RAG Context
    department_context: List[Dict[str, str]]  # Retrieved documents
    department_requirements: str  # Parsed requirements summary
    rag_metadata: Dict[str, Any]  # Retrieval metadata
    
    # Evaluation Data
    candidate_answer: str
    evaluation_score: float
    technical_score: float
    communication_score: float
    strengths: List[str]
    weaknesses: List[str]
    feedback_detail: str
    evaluation_metadata: Dict[str, Any]
    
    # Decision & Navigation
    next_action: str  # "continue", "deepen", "simplify", "evolve", "finish"
    suggested_follow_up: str
    next_phase: Optional[str]
    next_difficulty: Optional[int]
    
    # Time Tracking
    start_time: Optional[datetime]
    elapsed_time: Optional[int]
    
    # Complete Status
    is_complete: bool
    final_report: Optional[Dict[str, Any]]
    
    # Event Logging (for audit)
    nodes_executed: List[str]