import logging
import time
from app.graph.interview_state import InterviewState
from app.exceptions import LLMServiceError

logger = logging.getLogger(__name__)


async def question_generation_node(state: InterviewState) -> InterviewState:
    """
    Generate interview question using AI.
    - Main questions: interviewer_system + question_generation / adaptive_question
    - Probe follow-ups: followup_system + probe generation prompt
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    job_role = state.get('job_role')
    phase = state.get('current_phase')
    difficulty = state.get('difficulty_level', 1)
    conversation_history = state.get('conversation_history', [])
    department_requirements = state.get('department_requirements', '')
    candidate_profile = state.get('candidate_profile', '{}')
    question_number = state.get('question_number', 0)

    is_probe = state.get('inquisitor_action') == 'probe' or state.get('is_follow_up', False)
    probe_angle = state.get('probe_angle', '')
    probing_history = state.get('probing_history', [])
    main_question = state.get('main_question', state.get('current_question', ''))

    logger.info(f"Generating {'probe' if is_probe else 'main'} question: "
                f"Phase={phase}, Difficulty={difficulty}, Q#{question_number}")

    new_question_number = question_number

    history_summary = ""
    for h in conversation_history[-5:]:
        role = h.get('role', '')
        content = h.get('content', '')
        history_summary += f"\n{role}: {content}\n"

    try:
        llm_service = get_llm_service()

        if is_probe:
            system_prompt = load_prompt("system", "followup_system.md")

            last_answer = ""
            for h in reversed(conversation_history):
                if h.get('role') == 'user' and not last_answer:
                    last_answer = h.get('content', '')
                    break

            probe_context = f"""
You need to ask a PROBE / FOLLOW-UP question to dig deeper.

Main question: {main_question}
Probe angle: {probe_angle}
Candidate's last answer: {last_answer[:500] if last_answer else 'N/A'}
Previous probes on this topic:
{chr(10).join(f"- Q: {p.get('question', '')[:100]}" for p in probing_history[-3:])}

Rules for this probe:
1. It must connect to the candidate's previous answer on this topic
2. It should be a natural follow-up, not a new topic
3. 1-2 sentences, conversational, open-ended
4. Stay on the SAME topic as the main question
5. Don't repeat questions already asked in previous probes
6. If the candidate is struggling, ask a simpler clarifying question

Output ONLY the question text.
"""
            user_prompt = probe_context

        elif question_number == 1:
            system_prompt = load_prompt("system", "interviewer_system.md")
            user_prompt = load_prompt(
                "interview", "question_generation.md",
                job_role=job_role,
                phase=phase,
                difficulty_level=difficulty,
                difficulty=difficulty,
                target_competency=state.get('current_competency', 'general'),
                persona=state.get('persona', 'professional'),
                hypothesis='N/A (phase-driven mode)',
                competency_info='N/A',
                approach='N/A',
                followup_number=state.get('question_depth', 0),
                department_context=department_requirements[:2000] if department_requirements else "N/A",
                candidate_profile=candidate_profile[:500] if candidate_profile else "N/A",
                question_number=question_number,
                total_questions=state.get('total_questions', 10),
                conversation_history=history_summary or "(no previous conversation)"
            )
        else:
            system_prompt = load_prompt("system", "followup_system.md")

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

            user_prompt = load_prompt(
                "interview", "adaptive_question.md",
                job_role=job_role,
                phase=phase,
                previous_question=previous_question or "(first question)",
                candidate_answer=previous_answer or "(no answer yet)",
                difficulty_level=difficulty,
                previous_scores=scores_str,
                department_context=department_requirements[:1000] if department_requirements else "N/A"
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
Department context: {department_requirements[:500] if department_requirements else 'N/A'}

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

        logger.info(f"Generated {'probe' if is_probe else 'main'} question: {question[:100]}...")

        depth = state.get('question_depth', 0)
        new_depth = depth + 1 if is_probe else 0

        new_state: InterviewState = {
            **state,
            'current_question': question,
            'question_number': new_question_number,
            'question_depth': new_depth,
            'is_follow_up': is_probe,
            'main_question': main_question,
            'rag_metadata': {
                **state.get('rag_metadata', {}),
                'question_generated_by_ai': True,
                'question_number': new_question_number,
                'is_probe': is_probe,
                'probe_angle': probe_angle if is_probe else '',
                'question_depth': new_depth,
                'template_used': 'probe' if is_probe else ('adaptive_question' if question_number > 1 else 'question_generation'),
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
