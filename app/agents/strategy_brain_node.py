import json
import logging

from app.graph.interview_state import InterviewState
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.config.interview_styles import get_style, PERSONAS

logger = logging.getLogger(__name__)


async def strategy_brain_node(state: InterviewState) -> InterviewState:
    if state.get("strategy_cache_valid", False) and state.get("interview_strategy"):
        logger.info("Strategy brain: cache hit, skipping LLM")
        return state

    job_role = state.get("job_role", "Unknown")
    candidate_profile = state.get("candidate_profile", {})
    style_name = state.get("interview_style", {}).get("name", "STANDARD")
    style = get_style(style_name)

    try:
        from app.services.llm_service import get_llm_service
        from app.services.prompt_loader import load_prompt

        llm_service = get_llm_service()

        strengths = ", ".join(candidate_profile.get("strengths", []) or ["None identified"])
        weaknesses = ", ".join(candidate_profile.get("weaknesses", []) or ["None identified"])
        taxonomy = state.get("competency_taxonomy") or COMPETENCY_TAXONOMY
        comp_names = ", ".join(c["name"] for c in taxonomy[:10])

        prompt = load_prompt(
            "interview",
            "strategy_brain.md",
            job_role=job_role,
            style_name=style["name"],
            persona=style.get("persona", "friendly"),
            candidate_strengths=strengths,
            candidate_weaknesses=weaknesses,
            competency_list=comp_names,
            max_questions=str(style.get("max_questions", 10)),
            difficulty_min=str(style.get("difficulty_range", (1, 3))[0]),
            difficulty_max=str(style.get("difficulty_range", (1, 3))[1]),
        )

        response = await llm_service.invoke(
            prompt=prompt,
            temperature=0.3,
            max_tokens=800,
        )

        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        strategy = json.loads(response)
    except Exception as e:
        logger.warning(f"Strategy brain LLM failed: {e}, using defaults")
        strategy = _default_strategy(style, candidate_profile)

    strategy["style_applied"] = style["name"]
    strategy["persona"] = strategy.get("persona", style.get("persona", "friendly"))

    return {
        **state,
        "interview_strategy": strategy,
        "strategy_cache_valid": True,
        "persona": strategy.get("persona", "friendly"),
    }


def invalidate_cache(state: InterviewState) -> InterviewState:
    return {
        **state,
        "strategy_cache_valid": False,
    }


def _default_strategy(style: dict, candidate_profile: dict) -> dict:
    return {
        "phase_order": style.get("phase_order", ["intro", "technical", "behavioral", "conclusion"]),
        "competency_priority": style.get("base_competency_priority", {}),
        "difficulty_range": style.get("difficulty_range", (1, 3)),
        "persona": style.get("persona", "friendly"),
        "strategic_intent": "Standard evidence-driven interview",
        "early_termination_threshold": style.get("early_termination_threshold", 0.85),
    }
