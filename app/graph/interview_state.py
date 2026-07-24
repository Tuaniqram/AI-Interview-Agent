from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class InterviewState(TypedDict, total=False):
    session_id: str
    department_id: int
    candidate_id: str

    # Interview Context
    job_role: str
    flow_type: str

    # Conversation State
    conversation_history: List[Dict[str, str]]
    current_phase: str
    phase_stage: int

    # Question Management
    question_number: int
    total_questions: int
    current_question: str
    difficulty_level: int

    # Follow-up / Probing
    question_depth: int
    follow_up_count: int
    topic_saturated: bool
    probe_question: str
    probe_angle: str
    inquisitor_action: str
    is_follow_up: bool
    main_question: str
    probing_history: List[Dict[str, str]]

    # Skill model
    skills_tested: List[str]
    skills_weak: List[str]
    skills_uncovered: List[str]
    coverage_map: Dict[str, float]

    # RAG Context
    department_context: List[Dict[str, str]]
    department_requirements: str
    rag_metadata: Dict[str, Any]

    # Evaluation Data
    candidate_answer: str
    evaluation_score: float
    technical_score: float
    communication_score: float
    strengths: List[str]
    weaknesses: List[str]
    feedback_detail: str
    evaluation_metadata: Dict[str, Any]
    evaluation_failed: bool

    # Speech / Para-linguistic (voice mode)
    speech_metrics: Dict[str, float]

    # Decision & Navigation
    next_action: str
    suggested_follow_up: str
    next_phase: Optional[str]
    next_difficulty: Optional[int]

    # Time Tracking
    start_time: Optional[datetime]
    elapsed_time: Optional[int]

    # Complete Status
    is_complete: bool
    final_report: Optional[Dict[str, Any]]

    # Event Logging
    nodes_executed: List[str]
