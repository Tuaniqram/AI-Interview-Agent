"""
Phase Decision Node - LangGraph Node Agent
Decides the next phase, difficulty, and action for the upcoming question.
Uses LLM + phase_decision.md prompt for adaptive phase transitions.
"""
import json
import logging
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


async def phase_decision_node(state: InterviewState) -> InterviewState:
    """
    Decide the next interview phase, difficulty, and action.
    Called BEFORE question generation to determine what kind of question to ask.

    Args:
        state: Current interview state

    Returns:
        Updated state with phase decisions
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    current_phase = state.get('current_phase', 'intro')
    question_number = state.get('question_number', 1)
    total_questions = state.get('total_questions', 10)
    evaluation_score = state.get('evaluation_score')
    technical_score = state.get('technical_score')
    communication_score = state.get('communication_score')
    strengths = state.get('strengths', [])
    weaknesses = state.get('weaknesses', [])
    difficulty_level = state.get('difficulty_level', 1)

    history = state.get('conversation_history', [])
    conversation_summary = ""
    for h in history[-4:]:
        role = h.get('role', '')
        content = h.get('content', '')
        conversation_summary += f"\n{role}: {content[:200]}\n"

    logger.info(
        f"Phase decision: phase={current_phase}, q#{question_number}/{total_questions}, "
        f"score={evaluation_score}, diff={difficulty_level}"
    )

    try:
        llm_service = get_llm_service()

        prompt = load_prompt(
            "interview",
            "phase_decision.md",
            current_phase=current_phase,
            question_number=question_number,
            total_questions=total_questions,
            evaluation_score=str(evaluation_score) if evaluation_score is not None else "N/A",
            technical_score=str(technical_score) if technical_score is not None else "N/A",
            communication_score=str(communication_score) if communication_score is not None else "N/A",
            conversation_summary=conversation_summary or "(no conversation yet)",
            strengths=", ".join(strengths) if strengths else "None yet",
            weaknesses=", ".join(weaknesses) if weaknesses else "None yet",
            difficulty_history=str(difficulty_level),
        )

        logger.debug(f"Sending phase decision prompt ({len(prompt)} chars)")

        response = await llm_service.invoke(
            prompt=prompt,
            temperature=0.3,
            max_tokens=300
        )

        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        decision_data = None
        try:
            decision_data = json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    decision_data = json.loads(response[start:end + 1])
                except json.JSONDecodeError:
                    pass

        if not decision_data:
            logger.warning(f"Failed to parse phase decision JSON, using defaults. Response: {response[:200]}")
            return {
                **state,
                'next_phase': current_phase,
                'next_action': 'continue',
                'next_difficulty': difficulty_level,
                'suggested_follow_up': '',
                'rag_metadata': {
                    **state.get('rag_metadata', {}),
                    'phase_decision_failed': True,
                    'phase_decision_raw': response[:500]
                }
            }

        next_phase = decision_data.get('next_phase', current_phase)
        next_action = decision_data.get('next_action', 'continue')
        next_difficulty = decision_data.get('next_difficulty', difficulty_level)
        suggested_follow_up = decision_data.get('suggested_follow_up', '')
        reasoning = decision_data.get('reasoning', '')

        logger.info(
            f"Phase decision result: phase={next_phase}, action={next_action}, "
            f"diff={next_difficulty}, reason={reasoning[:80]}"
        )

        return {
            **state,
            'current_phase': next_phase,
            'next_phase': next_phase,
            'next_action': next_action,
            'next_difficulty': next_difficulty,
            'suggested_follow_up': suggested_follow_up,
            'rag_metadata': {
                **state.get('rag_metadata', {}),
                'phase_decision': {
                    'reasoning': reasoning,
                    'next_phase': next_phase,
                    'next_action': next_action,
                    'next_difficulty': next_difficulty
                }
            }
        }

    except Exception as e:
        logger.error(f"Phase decision failed: {e}")
        return {
            **state,
            'next_phase': current_phase,
            'next_action': 'continue',
            'next_difficulty': difficulty_level,
            'suggested_follow_up': '',
            'rag_metadata': {
                **state.get('rag_metadata', {}),
                'phase_decision_failed': True,
                'phase_decision_error': str(e)
            }
        }
