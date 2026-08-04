import json
import logging
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)

_MAX_PROBES_BY_PHASE = {
    "intro": 1,
    "experience": 2,
    "technical": 3,
    "behavioral": 2,
    "conclusion": 0,
}


async def inquisitor_node(state: InterviewState) -> InterviewState:
    """
    Decide whether to probe deeper into the current topic or saturate and move on.
    Uses LLM for the decision with clear heuristics as guardrails.

    Called AFTER answer_evaluator in the evaluation workflow.
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    question = state.get('current_question', '')
    candidate_answer = state.get('candidate_answer', '')
    depth = state.get('question_depth', 0)
    follow_up_count = state.get('follow_up_count', 0)
    phase = state.get('current_phase', 'intro')
    job_role = state.get('job_role', 'Unknown')
    difficulty = state.get('difficulty_level', 1)
    score = state.get('evaluation_score')
    strengths = state.get('strengths', [])
    weaknesses = state.get('weaknesses', [])
    probing_history = state.get('probing_history', [])
    department_requirements = state.get('department_requirements', '')

    max_probes = _MAX_PROBES_BY_PHASE.get(phase, 2)

    # Hard guardrails (no LLM needed)
    if max_probes == 0 or depth >= max_probes:
        logger.info(f"Inquisitor: saturate (max probes {max_probes} reached, depth={depth})")
        return _build_saturate(state, "Maximum probes for this topic reached")

    if score is not None and score < 4.0 and depth > 0:
        logger.info(f"Inquisitor: saturate (score {score} < 4.0, candidate struggling)")
        return _build_saturate(state, "Candidate is struggling with this topic")

    if score is not None and score < 3.0:
        logger.info(f"Inquisitor: saturate (score {score} < 3.0, fundamental misunderstanding)")
        return _build_saturate(state, "Candidate lacks foundational understanding of this topic")

    # Heuristic: very short answer on main question → always probe
    if depth == 0 and len(candidate_answer.split()) < 15:
        logger.info("Inquisitor: probe (very brief answer on main question)")
        return _build_probe(state, "Ask for specific examples or details to elaborate on their brief answer")

    # Heuristic: strong candidate, probe depth
    if depth == 0 and score is not None and score >= 8.0:
        logger.info("Inquisitor: probe (strong score, test depth)")
        return _build_probe(state, "Test deeper understanding — ask about trade-offs, edge cases, or advanced scenarios")

    # Heuristic: weakness identified, probe gently
    if depth == 0 and weaknesses and score is not None and 4.0 <= score < 7.0:
        logger.info("Inquisitor: probe (weakness identified, gentle follow-up)")
        return _build_probe(state, f"Gently probe the identified weakness: {weaknesses[0]}")

    # LLM-based decision for complex cases
    try:
        llm_service = get_llm_service()

        previous_probe_scores = []
        for entry in probing_history:
            s = entry.get('score')
            if s is not None:
                previous_probe_scores.append(str(s))

        prompt = load_prompt(
            "interview",
            "inquisitor.md",
            job_role=job_role,
            phase=phase,
            difficulty_level=difficulty,
            question=question,
            candidate_answer=candidate_answer,
            question_depth=str(depth),
            follow_up_count=str(follow_up_count),
            previous_probe_scores=", ".join(previous_probe_scores) if previous_probe_scores else "None",
            strengths=", ".join(strengths) if strengths else "None",
            weaknesses=", ".join(weaknesses) if weaknesses else "None",
            department_context=department_requirements[:800] if department_requirements else "N/A",
        )

        response = await llm_service.invoke(
            prompt=prompt,
            temperature=0.2,
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

        data = None
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(response[start:end + 1])
                except json.JSONDecodeError:
                    pass

        if data and data.get('inquisitor_action') in ('probe', 'saturate'):
            action = data['inquisitor_action']
            angle = data.get('probe_angle', '')
            reasoning = data.get('reasoning', '')
            logger.info(f"Inquisitor: {action} (LLM) — {reasoning}")

            if action == 'probe':
                return _build_probe(state, angle)
            else:
                return _build_saturate(state, reasoning)

        logger.warning(f"Inquisitor LLM returned invalid action, defaulting to heuristic. Response: {response[:200]}")
    except Exception as e:
        logger.warning(f"Inquisitor LLM failed: {e}, falling back to heuristic")

    # Final heuristic fallback
    if score is not None and score >= 7.0 and depth < max_probes:
        return _build_probe(state, "Probe deeper on a related aspect of their answer")
    if score is not None and score < 5.0 and depth == 0:
        return _build_saturate(state, "Score indicates fundamental gaps")

    return _build_saturate(state, "Default: move to next topic")


def _build_probe(state: InterviewState, probe_angle: str) -> InterviewState:
    return {
        **state,
        'inquisitor_action': 'probe',
        'probe_angle': probe_angle,
        'next_action': 'probe',
        'rag_metadata': {
            **state.get('rag_metadata', {}),
            'inquisitor': {
                'action': 'probe',
                'probe_angle': probe_angle,
                'depth': state.get('question_depth', 0),
            }
        }
    }


def _build_saturate(state: InterviewState, reasoning: str) -> InterviewState:
    return {
        **state,
        'inquisitor_action': 'saturate',
        'probe_angle': '',
        'rag_metadata': {
            **state.get('rag_metadata', {}),
            'inquisitor': {
                'action': 'saturate',
                'reasoning': reasoning,
                'depth': state.get('question_depth', 0),
            }
        }
    }
