"""
Answer Evaluation Node - LangGraph Node Agent
Evaluates candidate answers with detailed scoring and feedback.
Uses template system: evaluator_system (system) + answer_evaluation + scoring_rules (user).
"""
import json
import logging
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


async def answer_evaluator_node(state: InterviewState) -> InterviewState:
    """
    Evaluate candidate answer and provide detailed feedback.

    Args:
        state: Current interview state

    Returns:
        Updated state with evaluation results
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    job_role = state.get('job_role')
    question = state.get('current_question', '')
    candidate_answer = state.get('candidate_answer', '')
    department_requirements = state.get('department_requirements', '')
    difficulty = state.get('difficulty_level', 1)
    phase = state.get('current_phase')

    logger.info(f"Evaluating answer: Phase={phase}, Difficulty={difficulty}")

    try:
        llm_service = get_llm_service()

        system_prompt = load_prompt(
            "system",
            "evaluator_system.md"
        )

        eval_prompt = load_prompt(
            "evaluation",
            "answer_evaluation.md",
            job_role=job_role,
            question=question,
            candidate_answer=candidate_answer,
            phase=phase,
            difficulty_level=difficulty,
            department_context=department_requirements[:1000] if department_requirements else "N/A"
        )

        scoring_rules = load_prompt(
            "evaluation",
            "scoring_rules.md",
            job_role=job_role,
            question_type=phase,
            candidate_answer=candidate_answer[:500] if candidate_answer else "N/A",
            phase=phase,
            difficulty_level=difficulty
        )

        user_prompt = f"""{eval_prompt}

---

# Scoring Reference
{scoring_rules}
"""

        logger.debug(f"Sending evaluation prompt (system={len(system_prompt)} chars, user={len(user_prompt)} chars)")

        response = await llm_service.invoke(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1024
        )

        logger.info("Raw evaluation response: %s", response)

        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        score_data = None

        try:
            score_data = json.loads(response)
        except json.JSONDecodeError:
            logger.debug("Full response parse failed, attempting extraction")

        if not score_data:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    score_data = json.loads(response[start:end + 1])
                except json.JSONDecodeError as e:
                    logger.warning(f"Extracted JSON parse failed: {e}")

        if not score_data:
            logger.error(f"Failed to parse evaluation JSON. Response preview: {response[:200]}")
            raise ValueError("Failed to parse evaluation JSON")

        logger.info(f"Evaluation scored: score={score_data.get('score')}, technical={score_data.get('technical_score')}, communication={score_data.get('communication_score')}")

        return {
            **state,
            'evaluation_failed': False,
            'evaluation_score': float(score_data.get('score', 0.0)),
            'technical_score': float(score_data.get('technical_score', 0.0)),
            'communication_score': float(score_data.get('communication_score', 0.0)),
            'strengths': score_data.get('strengths', []),
            'weaknesses': score_data.get('weaknesses', []),
            'feedback_detail': score_data.get('feedback', ''),
            'next_action': score_data.get('next_action', 'continue'),
            'evaluation_metadata': {
                'raw_response': response,
                'templates_used': ['evaluator_system', 'answer_evaluation', 'scoring_rules']
            }
        }

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return {
            **state,
            'evaluation_failed': True,
            'evaluation_score': None,
            'technical_score': None,
            'communication_score': None,
            'strengths': [],
            'weaknesses': [],
            'feedback_detail': f"Evaluation failed: {e}",
            'next_action': 'retry',
            'evaluation_metadata': {'error': str(e), 'failed': True}
        }
