"""
Interview Flow Node - LangGraph Node Agent
Evaluates overall interview progress and recommends next phase/difficulty.
Uses LLM + interview_flow.md prompt for holistic flow management.
"""
import json
import logging
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


def _compute_phase_allocation(total_questions: int) -> str:
    """Dynamically allocate questions across phases based on total."""
    phases = ["intro", "experience", "technical", "behavioral", "conclusion"]
    if total_questions <= 0:
        counts = [0, 0, 0, 0, 0]
    elif total_questions <= 5:
        counts = [1 if i < total_questions else 0 for i in range(5)]
    else:
        counts = [2, 0, 0, 0, 0]
        remaining = total_questions - 2
        per_core = remaining // 3
        extra = remaining % 3
        counts[1] = per_core + (1 if extra >= 1 else 0)
        counts[2] = per_core + (1 if extra >= 2 else 0)
        counts[3] = per_core
        counts[4] = total_questions - sum(counts[:4])
    parts = [f"{phases[i]}: {counts[i]}" for i in range(5) if counts[i] > 0]
    return ", ".join(parts)


async def interview_flow_node(state: InterviewState) -> InterviewState:
    """
    Evaluate overall interview flow and recommend next phase/difficulty.
    Called AFTER answer evaluation to decide where to go next.

    Args:
        state: Current interview state

    Returns:
        Updated state with flow recommendations
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    job_role = state.get('job_role', 'Unknown')
    current_phase = state.get('current_phase', 'intro')
    question_number = state.get('question_number', 1)
    total_questions = state.get('total_questions', 10)
    evaluation_score = state.get('evaluation_score')

    scores = []
    rag_meta = state.get('rag_metadata', {})
    phase_decisions = rag_meta.get('phase_decisions', [])
    for d in phase_decisions:
        s = d.get('score')
        if s is not None:
            scores.append(str(s))

    performance_history = ", ".join(scores) if scores else "(no previous scores)"
    phase_allocation = _compute_phase_allocation(total_questions)

    logger.info(
        f"Interview flow: phase={current_phase}, q#{question_number}/{total_questions}, "
        f"allocation=[{phase_allocation}], score={evaluation_score}"
    )

    try:
        llm_service = get_llm_service()

        prompt = load_prompt(
            "interview",
            "interview_flow.md",
            job_role=job_role,
            current_phase=current_phase,
            current_question_number=str(question_number),
            total_questions=str(total_questions),
            phase_allocation=phase_allocation,
            overall_score=str(evaluation_score) if evaluation_score is not None else "N/A",
            performance_history=performance_history,
        )

        logger.debug(f"Sending interview flow prompt ({len(prompt)} chars)")

        response = await llm_service.invoke(
            prompt=prompt,
            temperature=0.3,
            max_tokens=400
        )

        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        flow_data = None
        try:
            flow_data = json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    flow_data = json.loads(response[start:end + 1])
                except json.JSONDecodeError:
                    pass

        if not flow_data:
            logger.warning(f"Failed to parse interview flow JSON, using defaults. Response: {response[:200]}")
            return _fallback(state, current_phase)

        next_phase = flow_data.get('next_phase', current_phase)
        next_difficulty = int(flow_data.get('next_difficulty_level', state.get('difficulty_level', 1)))
        notes = flow_data.get('notes', [])

        logger.info(
            f"Interview flow result: next_phase={next_phase}, "
            f"diff={next_difficulty}, notes={notes[:2]}"
        )

        phase_decisions = rag_meta.get('phase_decisions', [])
        phase_decisions.append({
            'phase': next_phase,
            'difficulty': next_difficulty,
            'score': evaluation_score,
            'notes': notes,
            'question_number': question_number,
        })

        return {
            **state,
            'next_phase': next_phase,
            'next_difficulty': next_difficulty,
            'rag_metadata': {
                **rag_meta,
                'phase_decisions': phase_decisions,
                'interview_flow': {
                    'next_phase': next_phase,
                    'next_difficulty': next_difficulty,
                    'notes': notes,
                }
            }
        }

    except Exception as e:
        logger.error(f"Interview flow decision failed: {e}")
        return _fallback(state, current_phase)


def _fallback(state: InterviewState, current_phase: str) -> InterviewState:
    """Fallback when LLM call fails — keep current phase."""
    return {
        **state,
        'next_phase': current_phase,
        'next_difficulty': state.get('difficulty_level', 1),
        'rag_metadata': {
            **state.get('rag_metadata', {}),
            'interview_flow_failed': True,
        }
    }
