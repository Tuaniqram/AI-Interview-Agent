"""
Competency resolution layer.

Determines which competency taxonomy an interview session uses so the engine can
interview for ANY field, not just software engineering.

Resolution order (first decisive wins):
    1. Scorecard template  (org-curated competencies, highest priority)
    2. Interview template  (department-level competencies)
    3. AI role profiler     (role-first: role context drives the LLM pass; the
                            cached result lands on the newest organization
                            interview template for reuse)
    4. Default taxonomy    (app/data/competency_taxonomy.py)

Thin scorecards — declarations with fewer than
``role_competency_profiler.MIN_SCORECARD_COMPETENCIES`` entries — are enriched
by the AI pass instead of being taken at face value, so a 3-competency generic
rubric cannot flatten a role's interview (F1).
"""
import logging
import re
from collections import OrderedDict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY, NON_IT_COMPETENCY_IDS
from app.intelligence.role_competency_profiler import (
    build_role_context,
    is_thin_scorecard,
    role_cache_key,
    suggest_competencies,
)
from app.models.db import InterviewTemplate, ScorecardTemplate

logger = logging.getLogger(__name__)

# In-memory LRU for AI-profiled resolutions: sha1 -> normalized entries.
_MAX_RESOLUTION_CACHE = 128
_RESOLUTION_CACHE: OrderedDict[str, list[dict]] = OrderedDict()

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
    "commerce": ["domain", "communication"],
    "marketing": ["domain", "completeness"],
    "design": ["domain", "communication"],
    "product": ["domain", "reasoning"],
    "hr": ["domain", "behavioral"],
    "finance": ["domain", "reasoning"],
    "operations": ["domain", "completeness"],
    "customer_success": ["domain", "communication"],
}

_FALLBACK_WEIGHTS = {
    "tech_core": 3.0,
    "tech_system_design": 3.0,
    "tech_event_driven": 3.0,
    "cog_problem_solving": 3.0,
    "behav_teamwork": 2.0,
    "behav_communication": 2.0,
    "tech_deployment": 2.0,
    "tech_caching": 2.0,
    "tech_data_modeling": 2.0,
    "com_sales_strategy": 3.0,
    "mkt_brand_strategy": 3.0,
    "des_ux_research": 2.0,
    "prd_product_strategy": 3.0,
    "hr_talent_acquisition": 2.0,
    "fin_financial_analysis": 3.0,
    "ops_process_improvement": 2.0,
    "cs_churn_retention": 2.0,
}


def default_taxonomy() -> list[dict]:
    """Default engine taxonomy with reflection weights applied (IT competencies only)."""
    return [
        {
            **dict(c),
            "weight": _FALLBACK_WEIGHTS.get(c["id"], 1.0),
            "max_score": 10.0,
        }
        for c in COMPETENCY_TAXONOMY
        if c["id"] not in NON_IT_COMPETENCY_IDS
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

        entry = {
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
        probe = str(item.get("verification_probe") or "").strip()
        if probe:
            entry["verification_probe"] = probe
        skills = [
            str(s).strip().lower()
            for s in (item.get("skills") or [])
            if str(s).strip()
        ]
        if skills:
            entry["skills"] = skills[:8]
        normalized.append(entry)
    return normalized


def derive_domain_label(taxonomy: list[dict]) -> str:
    """Label for the core knowledge dimension: technical interviews keep the
    existing label; any taxonomy without a technical category is a domain one."""
    if any(c.get("category") == "technical" for c in taxonomy):
        return "Technical Knowledge"
    return "Domain Knowledge"


# Fix 6: an interview targets at most this many competencies. The full
# taxonomy (15+ ids) spread the question budget so thin that coverage stayed
# near 0% and the interview never reached sufficiency.
MAX_REQUIRED_COMPETENCIES = 6


def derive_required_competencies(
    taxonomy: list[dict],
    priority_map: dict | None = None,
    max_competencies: int = MAX_REQUIRED_COMPETENCIES,
) -> list[str]:
    """Required competencies = HIGH/MEDIUM priority subset, capped.

    A role-resolved taxonomy (scorecard/template/AI profiler output) is
    already a focused, curated set — every entry is required, so the generic
    priority map (keyed to default-taxonomy ids) must never shrink it to a
    one-competency coverage denominator. Only the broad default taxonomy
    needs the HIGH/MEDIUM cut.
    """
    if taxonomy and len(taxonomy) <= max_competencies:
        return [c["id"] for c in taxonomy]
    priority_map = priority_map or {}
    high = [c["id"] for c in taxonomy if priority_map.get(c["id"]) == "HIGH"]
    medium = [c["id"] for c in taxonomy if priority_map.get(c["id"]) == "MEDIUM"]
    selected = (high + medium)[:max_competencies]
    if selected:
        return selected
    return [c["id"] for c in taxonomy][:max_competencies]


def taxonomy_for_state(
    taxonomy: list[dict],
    priority_map: dict | None = None,
    max_competencies: int = MAX_REQUIRED_COMPETENCIES,
) -> tuple[list[dict], list[str], str]:
    """Build the state slice needed by the interview engine.

    ``required`` is the HIGH/MEDIUM priority subset (capped at
    ``MAX_REQUIRED_COMPETENCIES``) so coverage and sufficiency targets a
    focused, achievable set instead of the whole taxonomy.
    """
    required = derive_required_competencies(taxonomy, priority_map, max_competencies)
    label = derive_domain_label(taxonomy)
    return taxonomy, required, label


async def _resolve_scorecard_defs(
    db: AsyncSession, scorecard_template_id: str | None
) -> list[dict]:
    """Org-curated scorecard competencies (highest priority)."""
    if not scorecard_template_id:
        return []
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
        return []


async def _resolve_template_defs(
    db: AsyncSession, org_id: int | None
) -> tuple[list[dict], InterviewTemplate | None]:
    """Organization interview-template competencies + the newest template row
    (the row the AI cache writes through to)."""
    if not org_id:
        return [], None
    try:
        result = await db.execute(
            select(InterviewTemplate)
            .where(InterviewTemplate.org_id == org_id)
            .order_by(InterviewTemplate.created_at.desc())
            .limit(10)
        )
        rows = list(result.scalars().all())
        newest = rows[0] if rows else None
        for template in rows:
            defs = _normalize(template.competencies)
            if defs:
                logger.info(
                    "Resolved %d competencies from interview template %s",
                    len(defs),
                    template.id,
                )
                return defs, newest
        return [], newest
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to resolve interview template competencies: %s", exc)
        return [], None


async def _db_suggestion_cache(db: AsyncSession, org_id: int | None) -> list[dict]:
    """Best-effort read of a previously persisted AI profile for the department."""
    if not org_id:
        return []
    try:
        result = await db.execute(
            select(InterviewTemplate)
            .where(
                InterviewTemplate.org_id == org_id,
                InterviewTemplate.suggested_competencies.is_not(None),
            )
            .order_by(InterviewTemplate.created_at.desc())
            .limit(1)
        )
        template = result.scalar_one_or_none()
        return _normalize(template.suggested_competencies if template else None)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read AI competency cache: %s", exc)
        return []


async def _persist_suggestion(
    db: AsyncSession,
    org_id: int | None,
    template_row: InterviewTemplate | None,
    entries: list[dict],
) -> None:
    """Best-effort write-through of an AI profile onto the newest organization
    interview template so future sessions resolve deterministically."""
    target = template_row
    if target is None and org_id:
        try:
            result = await db.execute(
                select(InterviewTemplate)
                .where(InterviewTemplate.org_id == org_id)
                .order_by(InterviewTemplate.created_at.desc())
                .limit(1)
            )
            target = result.scalars().first()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to locate template for AI cache write: %s", exc)
            return
    if target is None:
        return
    try:
        target.suggested_competencies = list(entries)
        await db.commit()
        logger.info("Persisted AI competency profile on template %s", target.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist AI competency cache: %s", exc)


async def _ai_pass(
    db: AsyncSession,
    role_context: dict | None,
    existing: list[dict] | None,
    org_id: int | None,
    template_row: InterviewTemplate | None,
    use_llm: bool,
) -> list[dict] | None:
    """Stage 3 — the role-first AI pass. Returns None when no role context
    exists or the pass fails, so callers fall through to the default taxonomy."""
    if not role_context:
        return None

    key = role_cache_key(role_context)
    cached = _RESOLUTION_CACHE.get(key)
    if cached is not None:
        _RESOLUTION_CACHE.move_to_end(key)
        logger.info("Resolved %d competencies from AI role cache (memory)", len(cached))
        return list(cached)

    db_cached = await _db_suggestion_cache(db, org_id)
    if db_cached:
        _RESOLUTION_CACHE[key] = list(db_cached)
        logger.info("Resolved %d competencies from AI role cache (db)", len(db_cached))
        return list(db_cached)

    entries, _source, _rationale = await suggest_competencies(
        role_context,
        existing_competencies=[
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "category": c.get("category"),
                "weight": c.get("weight"),
            }
            for c in (existing or [])
        ]
        if existing
        else None,
        use_llm=use_llm,
    )
    if not entries:
        return None
    _RESOLUTION_CACHE[key] = list(entries)
    await _persist_suggestion(db, org_id, template_row, entries)
    logger.info("Resolved %d competencies from AI role profiler", len(entries))
    return entries


async def _resolve_catalog_defs(db: AsyncSession, it_role_id) -> list[dict]:
    """The IT role's own competencies from the catalog (``role_competencies``).

    Curated and deterministic, so it ranks above the AI profiler: a catalog role never needs an
    LLM call to decide what to interview on. Core competencies come first, heaviest first.
    """
    if not it_role_id:
        return []
    from app.models.db import Competency, RoleCompetency

    rows = (
        await db.execute(
            select(RoleCompetency, Competency)
            .join(Competency, Competency.id == RoleCompetency.competency_id)
            .where(RoleCompetency.role_id == it_role_id, Competency.is_active.is_(True))
            .order_by(RoleCompetency.is_core.desc(), RoleCompetency.weight.desc(), Competency.id)
        )
    ).all()
    return _normalize(
        [
            {
                "id": comp.id,
                "name": comp.name,
                "category": comp.category,
                "weight": float(rc.weight) if rc.weight is not None else 1.0,
                "evidence_dimensions": list(comp.evidence_dimensions or []),
                "default_min_evidence": comp.default_min_evidence,
            }
            for rc, comp in rows
        ]
    )


async def resolve_competencies(
    db: AsyncSession,
    *,
    scorecard_template_id: str | None = None,
    org_id: int | None = None,
    role_context: dict | None = None,
    use_llm: bool = True,
    it_role_id=None,
) -> list[dict]:
    """Resolve the competency taxonomy for a new interview session.

    Order: scorecard -> org template -> IT role catalog (``it_role_id``) -> AI role profiler
    -> default IT taxonomy.

    ``role_context`` (see ``role_competency_profiler.build_role_context``)
    activates the role-first AI pass: thin scorecards and empty templates are
    enriched/proposed from the role, then cached. Pass ``use_llm=False`` to
    keep resolution fully deterministic (tests, offline runs).
    """
    scorecard_defs = await _resolve_scorecard_defs(db, scorecard_template_id)
    if scorecard_defs and not is_thin_scorecard(scorecard_defs):
        return scorecard_defs

    template_defs, template_row = await _resolve_template_defs(db, org_id)
    if template_defs and not is_thin_scorecard(template_defs):
        return template_defs

    # Order: scorecard -> org template -> IT role catalog -> AI profiler -> default taxonomy.
    catalog_defs = await _resolve_catalog_defs(db, it_role_id)
    if catalog_defs:
        return catalog_defs

    # Thin declarations are hints for the AI pass, not the final answer.
    existing = (scorecard_defs or template_defs or []) if role_context else None
    ai_entries = await _ai_pass(
        db,
        role_context,
        existing,
        org_id,
        template_row,
        use_llm,
    )
    if ai_entries:
        return ai_entries
    if existing:
        return existing

    logger.info("No curated competencies found, falling back to default taxonomy")
    return default_taxonomy()
