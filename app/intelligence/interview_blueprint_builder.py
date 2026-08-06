"""Interview blueprint builder — the V5 strategic plan for a session.

Produces the ``interview_blueprint`` the engine injects at start: phases,
priority competencies, focus areas, probe strategy and scenario material.
The deterministic fallback is fully functional; the LLM pass (guarded) tailors
it to the company brain and job role.
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
    use_llm: bool = True,
) -> dict:
    """Build an ``interview_blueprint`` dict (best-effort)."""
    style = style or get_style()
    style_name = style.get("name", "STANDARD")

    fallback = _default_blueprint(job_role, style, required_competencies, company_brain)

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
            competency_list=", ".join(c["name"] for c in COMPETENCY_TAXONOMY[:10]),
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
        return blueprint
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Interview blueprint LLM failed ({exc}); using fallback")
        return fallback


def _default_blueprint(
    job_role: str,
    style: dict,
    required_competencies: list[str] | None,
    company_brain: dict | None,
) -> dict:
    phases = style.get("phase_order", ["intro", "technical", "behavioral", "conclusion"])
    priorities = [
        c for c in COMPETENCY_TAXONOMY
        if c["id"] in (required_competencies or []) or c["category"] == "technical"
    ]
    tech_focus = (company_brain or {}).get("tech_stack", [])[:6]

    return {
        "version": "v1",
        "job_role": job_role,
        "style_applied": style.get("name", "STANDARD"),
        "phases": phases,
        "priority_competencies": [
            {"id": c["id"], "name": c["name"], "weight": 1.0}
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
