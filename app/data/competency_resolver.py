"""
Competency resolution layer.

Determines which competency taxonomy an interview session uses so the engine can
interview for ANY field, not just software engineering.

Resolution order (first non-empty wins):
    1. Scorecard template  (org-curated competencies, highest priority)
    2. Interview template  (department-level competencies)
    3. Default taxonomy    (app/data/competency_taxonomy.py)
"""
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY
from app.models.db import InterviewTemplate, ScorecardTemplate

logger = logging.getLogger(__name__)

CANONICAL_DIMENSIONS = {
    "technical",
    "communication",
    "behavioral",
    "reasoning",
    "confidence",
    "completeness",
    "domain",
}

DEFAULT_DIMENSIONS_BY_CATEGORY = {
    "technical": ["technical", "completeness"],
    "behavioral": ["behavioral", "communication"],
    "cognitive": ["reasoning", "completeness"],
    "experience": ["domain", "completeness"],
}

_FALLBACK_WEIGHTS = {
    "tech_core": 3.0,
    "tech_system_design": 3.0,
    "cog_problem_solving": 3.0,
    "behav_teamwork": 2.0,
    "behav_communication": 2.0,
}


def default_taxonomy() -> list[dict]:
    """Default engine taxonomy with reflection weights applied."""
    return [
        {
            **dict(c),
            "weight": _FALLBACK_WEIGHTS.get(c["id"], 1.0),
            "max_score": 10.0,
        }
        for c in COMPETENCY_TAXONOMY
    ]


def _normalize(raw: object) -> list[dict]:
    """Normalize stored competency definitions into engine-ready dicts."""
    if not raw:
        return []
    if not isinstance(raw, list):
        logger.warning("Competencies field is not a list (got %s), ignoring", type(raw).__name__)
        return []

    normalized = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        comp_id = str(item.get("id") or item.get("competency_id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not comp_id or not name:
            continue

        category = str(item.get("category") or "general").strip().lower() or "general"
        dims = item.get("evidence_dimensions") or DEFAULT_DIMENSIONS_BY_CATEGORY.get(
            category, ["domain", "completeness"]
        )
        dims = [d for d in dims if d in CANONICAL_DIMENSIONS] or [
            "domain",
            "completeness",
        ]

        normalized.append(
            {
                "id": comp_id.replace(" ", "_").lower(),
                "name": name,
                "category": category,
                "weight": float(item.get("weight") or 1.0),
                "max_score": float(item.get("max_score") or 10.0),
                "evidence_dimensions": dims,
                "default_min_evidence": int(
                    item.get("default_min_evidence") or item.get("min_evidence") or 2
                ),
            }
        )
    return normalized


def derive_domain_label(taxonomy: list[dict]) -> str:
    """Label for the core knowledge dimension: technical interviews keep the
    existing label; any taxonomy without a technical category is a domain one."""
    if any(c.get("category") == "technical" for c in taxonomy):
        return "Technical Knowledge"
    return "Domain Knowledge"


def taxonomy_for_state(taxonomy: list[dict]) -> tuple[list[dict], list[str], str]:
    """Build the state slice needed by the interview engine."""
    required = [c["id"] for c in taxonomy]
    label = derive_domain_label(taxonomy)
    return taxonomy, required, label


async def resolve_competencies(
    db: AsyncSession,
    *,
    scorecard_template_id: str | None = None,
    department_id: int | None = None,
) -> list[dict]:
    """Resolve the competency taxonomy for a new interview session."""
    if scorecard_template_id:
        try:
            result = await db.execute(
                select(ScorecardTemplate).where(
                    ScorecardTemplate.id == UUID(str(scorecard_template_id))
                )
            )
            template = result.scalar_one_or_none()
            defs = _normalize(template.competencies if template else None)
            if defs:
                logger.info(
                    "Resolved %d competencies from scorecard template %s",
                    len(defs),
                    scorecard_template_id,
                )
                return defs
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to resolve scorecard template competencies: %s", exc)

    if department_id:
        try:
            result = await db.execute(
                select(InterviewTemplate)
                .where(InterviewTemplate.department_id == department_id)
                .order_by(InterviewTemplate.created_at.desc())
                .limit(10)
            )
            for template in result.scalars().all():
                defs = _normalize(template.competencies)
                if defs:
                    logger.info(
                        "Resolved %d competencies from interview template %s",
                        len(defs),
                        template.id,
                    )
                    return defs
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to resolve interview template competencies: %s", exc)

    logger.info("No curated competencies found, falling back to default taxonomy")
    return default_taxonomy()
