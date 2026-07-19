"""
Interviewer Decision Node - LangGraph Node Agent
Makes adaptive decisions about next question, phase evolution, and difficulty.
Uses LLM for intelligent phase transitions with hardcoded safety fallbacks.
"""
import json
import logging
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


async def decision_node(state: InterviewState) -> InterviewState:
    """
    Make adaptive decisions for the next Interview step.
    Uses LLM to determine phase transitions, difficulty adjustment, and next action.
    
    Args:
        state: Current interview state
        
    Returns:
        Updated state with decisions
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    # Extract current state
    phase = state.get('current_phase')
    question_number = state.get('question_number', 0)
    score = state.get('evaluation_score', 7.0)
    difficulty = state.get('difficulty_level', 1)
    tech_score = state.get('technical_score', 7.0)
    communication_score = state.get('communication_score', 7.0)
    total_questions = state.get('total_questions', 10)
    conversation_history = state.get('conversation_history', [])
    strengths = state.get('strengths', [])
    weaknesses = state.get('weaknesses', [])
    difficulty_history = state.get('previous_difficulties', [1]) + [difficulty] if 'previous_difficulties' in state else [1, difficulty]

    logger.info(f"Making decision: Phase={phase}, Q#{question_number}/{total_questions}, Score={score}, Difficulty={difficulty}")

    next_action = 'continue'
    next_phase = phase
    next_difficulty = difficulty
    suggested_follow_up = ""

    # Safety check: evaluation failed
    evaluation_failed = state.get('evaluation_failed', False)
    if evaluation_failed:
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

    # Try LLM-driven phase decision
    try:
        llm_service = get_llm_service()

        # Build conversation summary
        conversation_summary = ""
        for h in conversation_history[-4:]:
            role = h.get('role', '')
            content = h.get('content', '')[:150]
            conversation_summary += f"\n{role}: {content}"
        if not conversation_summary:
            conversation_summary = "(no recent conversation)"

        prompt = load_prompt(
            "interview",
            "phase_decision.md",
            current_phase=phase,
            question_number=question_number,
            total_questions=total_questions,
            evaluation_score=score,
            technical_score=tech_score,
            communication_score=communication_score,
            conversation_summary=conversation_summary,
            strengths=", ".join(strengths) if strengths else "none recorded",
            weaknesses=", ".join(weaknesses) if weaknesses else "none recorded",
            difficulty_history=str(difficulty_history)
        )

        response = await llm_service.invoke(
            prompt=prompt,
            temperature=0.3,
            max_tokens=300
        )

        # Parse JSON response
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        decision = json.loads(response)

        next_phase = decision.get("next_phase", phase)
        next_action = decision.get("next_action", "continue")
        next_difficulty = decision.get("next_difficulty", difficulty)
        suggested_follow_up = decision.get("suggested_follow_up", "")

        logger.info(f"LLM decision: Action={next_action}, Phase={next_phase}, Difficulty={next_difficulty}")

    except Exception as e:
        logger.warning(f"LLM phase decision failed, using rule-based fallback: {e}")
        # Fallback: simple difficulty adapt and phase progression
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

        # Phase progression fallback
        phase_order = ["intro", "experience", "technical", "behavioral", "conclusion"]
        phase_index = phase_order.index(phase) if phase in phase_order else -1
        if phase_index < len(phase_order) - 1 and question_number >= (total_questions * (phase_index + 1)) // len(phase_order):
            next_phase = phase_order[phase_index + 1]

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
