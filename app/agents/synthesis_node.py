import json
import logging
from typing import List, Dict, Any
from app.graph.interview_state import InterviewState

logger = logging.getLogger(__name__)


async def synthesis_node(state: InterviewState) -> InterviewState:
    """
    Generate a holistic final report synthesizing all evaluations.
    Goes beyond score-averaging — assesses growth trajectory, consistency,
    difficulty reached, and produces a narrative assessment.
    """
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    job_role = state.get('job_role', 'Unknown')
    conversation_history = state.get('conversation_history', [])
    skills_tested = state.get('skills_tested', [])
    skills_weak = state.get('skills_weak', [])
    coverage_map = state.get('coverage_map', {})
    rag_metadata = state.get('rag_metadata', {})
    phase_decisions = rag_metadata.get('phase_decisions', [])

    evaluation_history = []
    current_strengths = set()
    current_weaknesses = set()

    for msg in conversation_history:
        if msg.get('role') == 'user' and msg.get('content'):
            evaluation_history.append({
                'answer': msg.get('content', ''),
            })

    # Build score timeline from phase decisions
    score_timeline = []
    for d in phase_decisions:
        s = d.get('score')
        if s is not None:
            score_timeline.append({
                'phase': d.get('phase', 'unknown'),
                'score': s,
                'question': d.get('question_number', 0),
            })

    avg_scores = [s['score'] for s in score_timeline if s['score'] is not None]
    avg_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0

    # Detect growth trend
    growth_trend = "stable"
    if len(avg_scores) >= 3:
        first_half = sum(avg_scores[:len(avg_scores)//2]) / (len(avg_scores)//2)
        second_half = sum(avg_scores[len(avg_scores)//2:]) / (len(avg_scores) - len(avg_scores)//2)
        if second_half - first_half > 0.5:
            growth_trend = "improving"
        elif first_half - second_half > 0.5:
            growth_trend = "declining"

    max_difficulty = state.get('difficulty_level', 1)

    try:
        llm_service = get_llm_service()

        synthesis_prompt = load_prompt(
            "evaluation",
            "synthesis.md",
            job_role=job_role,
            score_timeline=json.dumps(score_timeline, indent=2),
            avg_score=f"{avg_score:.1f}",
            growth_trend=growth_trend,
            max_difficulty=f"Level {max_difficulty}/3",
            skills_tested=json.dumps(skills_tested, indent=2) if skills_tested else "None recorded",
            skills_weak=json.dumps(skills_weak, indent=2) if skills_weak else "None identified",
            coverage_map=json.dumps(coverage_map, indent=2) if coverage_map else "No coverage data",
        )

        response = await llm_service.invoke(
            prompt=synthesis_prompt,
            temperature=0.3,
            max_tokens=800
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
            logger.warning(f"Synthesis LLM returned invalid JSON, using fallback: {response[:200]}")
            return _fallback_synthesis(state, avg_score, skills_tested, skills_weak, growth_trend)

        logger.info(f"Synthesis complete: holistic_score={data.get('holistic_score')}, "
                     f"fit={data.get('fit_assessment')}")

        return {
            **state,
            'final_report': {
                'holistic_score': data.get('holistic_score', avg_score),
                'average_score': round(avg_score, 1),
                'growth_trend': growth_trend,
                'narrative': data.get('narrative', ''),
                'key_strengths': data.get('key_strengths', list(skills_tested)[:3]),
                'key_weaknesses': data.get('key_weaknesses', list(skills_weak)[:3]),
                'fit_assessment': data.get('fit_assessment', 'Potential Fit'),
                'interview_notes': data.get('interview_notes', ''),
                'skills_tested': skills_tested,
                'skills_weak': skills_weak,
                'coverage_map': coverage_map,
                'max_difficulty_reached': max_difficulty,
                'score_timeline': score_timeline,
            },
            'rag_metadata': {
                **rag_metadata,
                'synthesis': {
                    'performed': True,
                    'holistic_score': data.get('holistic_score'),
                    'fit_assessment': data.get('fit_assessment'),
                }
            }
        }

    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        return _fallback_synthesis(state, avg_score, skills_tested, skills_weak, growth_trend)


def _fallback_synthesis(
    state: InterviewState,
    avg_score: float,
    skills_tested: List[str],
    skills_weak: List[str],
    growth_trend: str,
) -> InterviewState:
    """Fallback synthesis when LLM fails."""
    return {
        **state,
        'final_report': {
            'holistic_score': round(avg_score, 1),
            'average_score': round(avg_score, 1),
            'growth_trend': growth_trend,
            'narrative': f"Candidate completed the interview with an average score of {avg_score:.1f}/10.",
            'key_strengths': skills_tested[:3] if skills_tested else [],
            'key_weaknesses': skills_weak[:3] if skills_weak else [],
            'fit_assessment': 'Potential Fit',
            'interview_notes': '',
            'skills_tested': skills_tested,
            'skills_weak': skills_weak,
            'coverage_map': state.get('coverage_map', {}),
            'max_difficulty_reached': state.get('difficulty_level', 1),
            'score_timeline': [],
        }
    }
