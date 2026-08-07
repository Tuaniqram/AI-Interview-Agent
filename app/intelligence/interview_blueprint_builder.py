"""Interview blueprint builder — the V5 strategic plan for a session.

Produces the ``interview_blueprint`` the engine injects at start: phases,
priority competencies, focus areas, probe strategy and scenario material.

Role-first (F1): the competency set is FIXED by the role's resolved taxonomy
(scorecard → template → AI role profiler → default) — the company brain only
grounds the scenario material (tech stack, focus areas). The LLM pass tailors
scenarios to the company; it never redefines the competencies.
"""
import logging

from app.config.interview_styles import get_style
from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.intelligence._helpers import parse_llm_json_with_retry

logger = logging.getLogger(__name__)


async def build_interview_blueprint(
    *,
    job_role: str,
    company_brain: dict | None = None,
    style: dict | None = None,
    required_competencies: list[str] | None = None,
    competency_taxonomy: list[dict] | None = None,
    use_llm: bool = True,
) -> dict:
    """Build an ``interview_blueprint`` dict (best-effort)."""
    style = style or get_style()
    style_name = style.get("name", "STANDARD")
    taxonomy = competency_taxonomy or COMPETENCY_TAXONOMY

    fallback = _default_blueprint(job_role, style, required_competencies, company_brain, taxonomy)

    if not use_llm:
        return fallback

    try:
        from app.services.llm_service import get_llm_service
        from app.services.prompt_loader import load_prompt

        tech_focus = (company_brain or {}).get("tech_stack", [])[:8]
        focus_areas = (company_brain or {}).get("focus_areas", [])

        prompt = load_prompt(
            "intelligence",
            "interview_blueprint.md",
            job_role=job_role or "Unknown",
            style_name=style_name,
            persona=style.get("persona", "friendly"),
            tech_stack=", ".join(tech_focus) or "not specified",
            competency_list=", ".join(c["name"] for c in taxonomy),
            difficulty_min=str(style.get("difficulty_range", (1, 3))[0]),
            difficulty_max=str(style.get("difficulty_range", (1, 3))[1]),
            focus_areas=", ".join(focus_areas) or "not specified",
        )

        data = await parse_llm_json_with_retry(
            get_llm_service(), prompt, temperature=0.3, max_tokens=800, tier="cheap"
        )
        blueprint = {**fallback, **data}
        blueprint["version"] = "v1"
        blueprint["job_role"] = job_role
        blueprint["style_applied"] = style_name
        blueprint["source"] = "llm"
        # The competency set is role-locked — the LLM may never override it.
        blueprint["priority_competencies"] = fallback["priority_competencies"]
        blueprint["focus_areas"] = fallback["focus_areas"]
        return blueprint
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Interview blueprint LLM failed ({exc}); using fallback")
        return fallback


def _default_blueprint(
    job_role: str,
    style: dict,
    required_competencies: list[str] | None,
    company_brain: dict | None,
    taxonomy: list[dict],
) -> dict:
    phases = style.get("phase_order", ["intro", "technical", "behavioral", "conclusion"])
    priorities = [
        c for c in taxonomy
        if c["id"] in (required_competencies or []) or c["category"] == "technical"
    ]
    if not priorities:
        priorities = list(taxonomy)
    # Only the role's focus areas — company tech stack is scenario material.
    tech_focus = (company_brain or {}).get("tech_stack", [])[:6]

    return {
        "version": "v1",
        "job_role": job_role,
        "style_applied": style.get("name", "STANDARD"),
        "phases": phases,
        "priority_competencies": [
            {
                "id": c["id"],
                "name": c["name"],
                "weight": float(c.get("weight") or 1.0),
            }
            for c in priorities[:8]
        ],
        "focus_areas": [c["name"] for c in priorities[:6]],
        "probe_strategy": {
            "depth": "adaptive",
            "max_follow_ups": 2,
            "style": "evidence-first",
        },
        "tech_stack_focus": tech_focus,
        "scenarios": [],
        "source": "fallback",
    }
