"""
Question Generation Node - LangGraph Node Agent
Generates adaptive interview questions using LLM and company context.
CRITICAL: NO HARDCODED TEMPLATES - Always generates via AI.
"""
import logging
import time
from app.graph.interview_state import InterviewState
from app.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


async def question_generation_node(state: InterviewState) -> InterviewState:
    """
    Generate the next interview question using AI.
    Uses template system:
    - Question #1: interviewer_system + question_generation
    - Question #2+: followup_system + adaptive_question

    Args:
        state: Current interview state

    Returns:
        Updated state with generated question
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    job_role = state.get('job_role')
    phase = state.get('current_phase')
    difficulty = state.get('difficulty_level', 1)
    conversation_history = state.get('conversation_history', [])
    company_requirements = state.get('company_requirements', '')
    candidate_profile = state.get('candidate_profile', '{}')
    question_number = state.get('question_number', 0)

    logger.info(f"Generating adaptive question: Phase={phase}, Difficulty={difficulty}, Q#{question_number}")

    new_question_number = question_number

    history_summary = ""
    for h in conversation_history[-5:]:
        role = h.get('role', '')
        content = h.get('content', '')
        history_summary += f"\n{role}: {content}\n"

    try:
        llm_service = get_llm_service()

        if question_number == 1:
            system_prompt = load_prompt(
                "system",
                "interviewer_system.md"
            )
            user_prompt = load_prompt(
                "interview",
                "question_generation.md",
                job_role=job_role,
                phase=phase,
                difficulty_level=difficulty,
                company_context=company_requirements[:2000] if company_requirements else "N/A",
                candidate_profile=candidate_profile[:500] if candidate_profile else "N/A",
                question_number=question_number,
                total_questions=state.get('total_questions', 10),
                conversation_history=history_summary or "(no previous conversation)"
            )
        else:
            previous_question = ""
            previous_answer = ""
            for h in reversed(conversation_history):
                if h.get('role') == 'user' and not previous_answer:
                    previous_answer = h.get('content', '')
                elif h.get('role') == 'assistant' and not previous_question:
                    previous_question = h.get('content', '')
                if previous_question and previous_answer:
                    break

            scores = state.get('previous_scores', [])
            scores_str = str(scores) if scores else "[]"

            system_prompt = load_prompt(
                "system",
                "followup_system.md"
            )
            user_prompt = load_prompt(
                "interview",
                "adaptive_question.md",
                job_role=job_role,
                phase=phase,
                previous_question=previous_question or "(first question)",
                candidate_answer=previous_answer or "(no answer yet)",
                difficulty_level=difficulty,
                previous_scores=scores_str,
                company_context=company_requirements[:1000] if company_requirements else "N/A"
            )

        logger.debug(f"Sending prompt to LLM (system={len(system_prompt)} chars, user={len(user_prompt)} chars)")

        t0 = time.time()
        question = await llm_service.invoke(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=200
        )
        logger.info(f"LLM call completed in {time.time() - t0:.2f}s (q#{question_number}, phase={phase})")

        question = question.strip()
        if question.startswith("Question:"):
            question = question[9:].strip()

        if not question:
            logger.warning("LLM returned empty question, retrying with simplified prompt")
            simplified_prompt = f"""
You are an interviewer for the role: {job_role}.
Phase: {phase}. Difficulty: {difficulty}.
Company context: {company_requirements[:500] if company_requirements else 'N/A'}

Generate ONE adaptive interview question. Output ONLY the question text.
"""
            question = await llm_service.invoke(
                prompt=simplified_prompt,
                temperature=0.9,
                max_tokens=200
            )
            question = question.strip()
            if question.startswith("Question:"):
                question = question[9:].strip()

            if not question:
                logger.error("LLM returned empty question after retry")
                raise LLMServiceError("LLM failed to generate a valid question after retry")

        logger.info(f"Generated adaptive question: {question[:100]}...")

        new_state: InterviewState = {
            **state,
            'current_question': question,
            'question_number': new_question_number,
            'rag_metadata': {
                **state.get('rag_metadata', {}),
                'question_generated_by_ai': True,
                'question_number': new_question_number,
                'template_used': 'adaptive_question' if question_number > 1 else 'question_generation',
                'ai_generation_params': {
                    'temperature': 0.8,
                    'max_tokens': 200
                }
            }
        }

        return new_state

    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        new_state: InterviewState = {
            **state,
            'current_question': None,
            'question_number': question_number,
            'rag_metadata': {
                **state.get('rag_metadata', {}),
                'question_generated_by_ai': False,
                'question_generation_failed': True,
                'error': str(e)
            }
        }
        raise
