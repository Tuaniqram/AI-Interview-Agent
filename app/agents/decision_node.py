"""
Interviewer Decision Node - LangGraph Node Agent
Makes adaptive decisions about next question, phase evolution, and difficulty.
Rule-based only — fast (~5ms), no LLM call needed.
"""
import logging
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)

_PHASE_ORDER = ["intro", "experience", "technical", "behavioral", "conclusion"]


async def decision_node(state: InterviewState) -> InterviewState:
    """
    Make adaptive decisions for the next Interview step.
    Rule-based logic for difficulty adjustment and phase progression.

    Args:
        state: Current interview state

    Returns:
        Updated state with decisions
    """
    phase = state.get('current_phase')
    question_number = state.get('question_number', 0)
    score = state.get('evaluation_score', 7.0)
    difficulty = state.get('difficulty_level', 1)
    total_questions = state.get('total_questions', 10)

    logger.info(f"Decision: Phase={phase}, Q#{question_number}/{total_questions}, Score={score}, Difficulty={difficulty}")

    next_action = 'continue'
    next_phase = phase
    next_difficulty = difficulty
    suggested_follow_up = ""

    # Safety check: evaluation failed
    if state.get('evaluation_failed', False):
        next_action = 'finish'
        suggested_follow_up = 'Evaluation system error - ending interview'
        logger.warning("Evaluation failed, ending interview loop")
        return _build_result(state, next_action, next_phase, next_difficulty, suggested_follow_up, score)

    # Safety check: max questions reached
    if question_number + 1 >= total_questions:
        next_action = 'finish'
        next_phase = "conclusion"
        suggested_follow_up = "Maximum questions reached - ending interview"
        logger.info(f"Max questions ({total_questions}) reached, ending interview")
        return _build_result(state, next_action, next_phase, next_difficulty, suggested_follow_up, score)

    # Difficulty adjustment based on score
    if score is not None and score >= 8.0 and difficulty < 3:
        next_difficulty = min(3, difficulty + 1)
        next_action = 'deepen'
        suggested_follow_up = "Probe deeper into technical implementation challenges"
    elif score is not None and score < 6.0 and difficulty > 1:
        next_difficulty = max(1, difficulty - 1)
        next_action = 'simplify'
        suggested_follow_up = "Simplify the question to build confidence"
    else:
        next_difficulty = difficulty
        next_action = 'continue'
        suggested_follow_up = "Continue with current difficulty level"

    # Phase progression
    phase_index = _PHASE_ORDER.index(phase) if phase in _PHASE_ORDER else -1
    if phase_index < len(_PHASE_ORDER) - 1 and question_number >= (total_questions * (phase_index + 1)) // len(_PHASE_ORDER):
        next_phase = _PHASE_ORDER[phase_index + 1]

    return _build_result(state, next_action, next_phase, next_difficulty, suggested_follow_up, score)


def _build_result(
    state: InterviewState,
    next_action: str,
    next_phase: str,
    next_difficulty: int,
    suggested_follow_up: str,
    score: float
) -> InterviewState:
    """Build the result state with decision metadata."""
    logger.info(f"Decision final: Action={next_action}, Phase={next_phase}, Difficulty={next_difficulty}")
    return {
        **state,
        'next_action': next_action,
        'next_phase': next_phase,
        'next_difficulty': next_difficulty,
        'suggested_follow_up': suggested_follow_up,
        'rag_metadata': {
            **state.get('rag_metadata', {}),
            'adaptive_decisions': {
                'score': score,
                'recommended_action': next_action,
                'recommended_phase': next_phase,
                'recommended_difficulty': next_difficulty,
                'suggested_follow_up': suggested_follow_up
            }
        }
    }
