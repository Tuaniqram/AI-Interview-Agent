import json
import logging
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


async def skill_tracker_node(state: InterviewState) -> InterviewState:
    """
    Extract skills from the evaluated answer and update the candidate's skill model.
    Builds a coverage map of tested vs. uncovered skills over the interview.

    Called AFTER inquisitor (on saturate) in the evaluation workflow.
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    question = state.get('current_question', '')
    candidate_answer = state.get('candidate_answer', '')
    job_role = state.get('job_role', 'Unknown')
    phase = state.get('current_phase', 'intro')
    score = state.get('evaluation_score')
    technical_score = state.get('technical_score')
    communication_score = state.get('communication_score')
    strengths = state.get('strengths', [])
    weaknesses = state.get('weaknesses', [])

    # Current skill model
    skills_tested = state.get('skills_tested', [])
    skills_weak = state.get('skills_weak', [])
    coverage_map = state.get('coverage_map', {})

    try:
        llm_service = get_llm_service()

        prompt = load_prompt(
            "interview",
            "skill_tracker.md",
            job_role=job_role,
            phase=phase,
            question=question,
            candidate_answer=candidate_answer[:1000] if candidate_answer else "N/A",
            evaluation_score=str(score) if score is not None else "N/A",
            technical_score=str(technical_score) if technical_score is not None else "N/A",
            communication_score=str(communication_score) if communication_score is not None else "N/A",
            strengths=", ".join(strengths) if strengths else "None",
            weaknesses=", ".join(weaknesses) if weaknesses else "None",
            currently_tested_skills=", ".join(skills_tested) if skills_tested else "None",
            currently_weak_skills=", ".join(skills_weak) if skills_weak else "None",
            coverage_map=str(coverage_map) if coverage_map else "{}",
        )

        response = await llm_service.invoke(
            prompt=prompt,
            temperature=0.2,
            max_tokens=500
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

        if not data:
            logger.warning(f"Skill tracker LLM returned invalid JSON: {response[:200]}")
            return _update_state_fallback(state)

        new_skills = data.get('new_skills', [])
        updated_skills = data.get('updated_skills', [])
        weak_identified = data.get('weak_skills_identified', [])
        uncovered_suggested = data.get('uncovered_areas_suggested', [])

        updated_tested = list(skills_tested)
        updated_weak = list(skills_weak)
        updated_coverage = dict(coverage_map)

        for skill in new_skills:
            name = skill.get('name', '').strip()
            s = skill.get('score')
            if name and name not in updated_tested:
                updated_tested.append(name)
                if s is not None:
                    updated_coverage[name] = float(s)
                if name in weak_identified or (s is not None and float(s) < 5.0):
                    if name not in updated_weak:
                        updated_weak.append(name)

        for skill in updated_skills:
            name = skill.get('name', '').strip()
            new_score = skill.get('new_score')
            if name and name in updated_tested and new_score is not None:
                old = updated_coverage.get(name, 0.0)
                updated_coverage[name] = round((old + float(new_score)) / 2, 1)

        updated_uncovered = uncovered_suggested if uncovered_suggested else state.get('skills_uncovered', [])

        logger.info(f"Skill tracker: {len(new_skills)} new skills, "
                     f"{len(updated_skills)} updated, "
                     f"{len(updated_weak)} weak, "
                     f"{len(updated_uncovered)} uncovered suggested")

        return {
            **state,
            'skills_tested': updated_tested,
            'skills_weak': updated_weak,
            'skills_uncovered': updated_uncovered,
            'coverage_map': updated_coverage,
            'rag_metadata': {
                **state.get('rag_metadata', {}),
                'skill_tracker': {
                    'new_skills': new_skills,
                    'updated_skills': updated_skills,
                    'weak_skills': weak_identified,
                    'uncovered_suggested': uncovered_suggested,
                }
            }
        }

    except Exception as e:
        logger.warning(f"Skill tracker failed: {e}")
        return _update_state_fallback(state)


def _update_state_fallback(state: InterviewState) -> InterviewState:
    return {
        **state,
        'rag_metadata': {
            **state.get('rag_metadata', {}),
            'skill_tracker_failed': True,
        }
    }
