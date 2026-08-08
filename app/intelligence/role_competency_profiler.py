"""Role competency profiler (F1) — AI-suggested competencies for a job role.

The engine derives the competency set for a session ROLE-FIRST:

    1. Org scorecard (thin scorecards — fewer than ``MIN_SCORECARD_COMPETENCIES``
       declared competencies — trigger the AI pass with the declared ones as hints)
    2. Department interview template (same thin rule)
    3. AI role profiler (LLM, schema-validated, cached)
    4. Default taxonomy

The profiler never interviews for a company: company context is grounding only,
so the same role produces a stable competency set regardless of org, while
role x company still differ in the final brain (company_brain, blueprint
scenarios, grounded questions).

Caching: in-memory LRU keyed by a sha1 of the role context, plus a best-effort
DB write-through (``interview_templates.suggested_competencies``) performed by
``app.data.competency_resolver`` — this module stays DB-free and pure.
"""
import hashlib
import json
import logging
import re
from collections import OrderedDict
from typing import Optional

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY, SKILL_TO_COMPETENCY

logger = logging.getLogger(__name__)

MIN_SCORECARD_COMPETENCIES = 4
MIN_SUGGESTED_COMPETENCIES = 4
MAX_SUGGESTED_COMPETENCIES = 6

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
_CATEGORY_PREFIXES = (
    "tech_",
    "behav_",
    "cog_",
    "exp_",
    "com_",
    "mkt_",
    "des_",
    "prd_",
    "hr_",
    "fin_",
    "ops_",
    "cs_",
)
_CATEGORIES = {
    "technical",
    "behavioral",
    "cognitive",
    "experience",
    "commerce",
    "marketing",
    "design",
    "product",
    "hr",
    "finance",
    "operations",
    "customer_success",
    "general",
}
_VALID_DIMENSIONS = {
    "technical",
    "communication",
    "behavioral",
    "reasoning",
    "confidence",
    "completeness",
    "domain",
}

# Family detection for the deterministic fallback: a role title/description is
# matched (most-specific first) onto the job family so a Marketing Manager with
# no declared skills still gets marketing competencies instead of tech ones.
_FAMILY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "product": (
        "product manager",
        "product owner",
        "product management",
        "head of product",
        "product lead",
    ),
    "design": (
        "designer",
        "ux",
        "user experience",
        "ui design",
        "visual design",
        "product design",
        "figma",
    ),
    "hr": ("hr", "recruiter", "recruiting", "talent", "people ops", "people operations"),
    "finance": (
        "finance",
        "accounting",
        "accountant",
        "controller",
        "fp&a",
        "cfo",
        "treasurer",
        "financial",
    ),
    "operations": (
        "operations",
        "supply chain",
        "logistics",
        "operations manager",
        "program manager",
        "chief of staff",
    ),
    "customer_success": (
        "customer success",
        "cs manager",
        "client success",
        "account manager",
        "renewal",
    ),
    "marketing": ("marketing", "growth", "seo", "brand", "content", "social media", "ppc", "cmo"),
    "commerce": (
        "sales",
        "account executive",
        "business development",
        "revenue",
        "quota",
        "partnership",
        "commercial",
    ),
}

_FAMILY_FALLBACKS: dict[str, tuple[str, ...]] = {
    "product": ("prd_product_strategy", "prd_roadmap_prioritization", "prd_user_stories"),
    "design": ("des_ux_research", "des_visual_design", "des_prototyping"),
    "hr": ("hr_talent_acquisition", "hr_employee_relations", "hr_org_design"),
    "finance": ("fin_financial_analysis", "fin_budgeting_forecasting", "fin_compliance_risk"),
    "operations": ("ops_process_improvement", "ops_project_management", "ops_kpi_management"),
    "customer_success": ("cs_onboarding", "cs_churn_retention", "cs_relationship_management"),
    "marketing": ("mkt_brand_strategy", "mkt_content_creation", "mkt_analytics_growth"),
    "commerce": ("com_sales_strategy", "com_customer_acumen", "com_negotiation"),
}

# Every family pads with these universal competencies after its own anchors.
_UNIVERSAL_FALLBACK = ("cog_problem_solving", "behav_communication", "exp_project_depth")

# Matches the pre-T1 tech fallback exactly so backend/frontend behaviour is unchanged.
_TECH_FAMILY_FALLBACK = ("tech_core", "cog_problem_solving", "behav_communication", "exp_project_depth")


def detect_family(job_role: str = "", description: str = "") -> str:
    """Map a role onto a job family ('technical' when nothing matches).

    The corpus is the role title first, then the description. Keys are matched
    in family order (product/design/hr/finance/operations/customer_success are
    checked before marketing/commerce so compound titles like "Sales Operations
    Manager" resolve to the more specific family).
    """
    corpus = " ".join(
        [str(job_role or "").lower(), str(description or "").lower()]
    )
    for family, keywords in _FAMILY_KEYWORDS.items():
        if any(kw in corpus for kw in keywords):
            return family
    return "technical"

# In-memory LRU: sha1(role context) -> {"entries": [...], "source": str}
_MAX_CACHE_ENTRIES = 128
_SUGGESTION_CACHE: "OrderedDict[str, dict]" = OrderedDict()


def build_role_context(
    *,
    job_role: str,
    skills_required: list | None = None,
    description: str = "",
    department_id: int | None = None,
    department_name: str = "",
    org_name: str = "",
    company_brain: dict | None = None,
) -> dict:
    """Serialize the role facts the profiler keys on (JSON-safe, cacheable)."""
    tech_stack: list = []
    if company_brain:
        tech_stack = company_brain.get("tech_stack") or company_brain.get(
            "technical_stack"
        ) or []
        tech_stack = list(tech_stack)[:12]
    return {
        "job_role": str(job_role or "").strip() or "Unknown",
        "skills_required": [str(s).strip() for s in (skills_required or []) if str(s).strip()][:20],
        "description": str(description or "").strip()[:2000],
        "department_id": department_id,
        "department_name": str(department_name or "").strip(),
        "org_name": str(org_name or "").strip(),
        "tech_stack": [str(t).strip() for t in tech_stack],
    }


def role_cache_key(role_context: dict) -> str:
    """Stable cache key for a role context (independent of dict key order)."""
    payload = json.dumps(role_context or {}, sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def is_thin_scorecard(competencies: list | None) -> bool:
    """A scorecard is thin when it declares competencies but fewer than the
    minimum a focused interview needs — those sessions get the AI pass."""
    if not competencies:
        return False
    return len(competencies) < MIN_SCORECARD_COMPETENCIES


def _normalize_entry(item: dict) -> Optional[dict]:
    """Validate one AI-suggested competency; returns None when invalid."""
    if not isinstance(item, dict):
        return None
    comp_id = str(item.get("id") or "").strip().lower()
    name = str(item.get("name") or "").strip()
    if not _ID_RE.match(comp_id) or not comp_id.startswith(_CATEGORY_PREFIXES):
        logger.warning("Role profiler: dropped competency with invalid id %r", comp_id)
        return None
    if not (3 <= len(name) <= 80):
        logger.warning("Role profiler: dropped competency with invalid name %r", name)
        return None

    category = str(item.get("category") or "general").strip().lower()
    if category not in _CATEGORIES:
        category = "general"

    dims = item.get("evidence_dimensions") or []
    dims = [str(d).strip().lower() for d in dims if str(d).strip().lower() in _VALID_DIMENSIONS]
    if not dims:
        dims = ["domain", "completeness"]

    try:
        weight = float(item.get("weight") or 1.0)
    except (TypeError, ValueError):
        weight = 1.0
    weight = min(3.0, max(1.0, weight))

    try:
        min_evidence = int(item.get("default_min_evidence") or 2)
    except (TypeError, ValueError):
        min_evidence = 2
    min_evidence = min(3, max(1, min_evidence))

    probe = str(item.get("verification_probe") or "").strip()
    if not probe:
        probe = f"Ask the candidate to demonstrate {name} with a concrete, quantified example"

    skills = [str(s).strip().lower() for s in (item.get("skills") or []) if str(s).strip()]
    skills = skills[:8]

    return {
        "id": comp_id,
        "name": name,
        "category": category,
        "weight": round(weight, 2),
        "max_score": 10.0,
        "evidence_dimensions": dims,
        "default_min_evidence": min_evidence,
        "verification_probe": probe,
        "skills": skills,
    }


def _validate_suggestions(data: dict) -> tuple[list[dict], str]:
    """Validate the LLM payload; returns (entries, rationale).

    Invalid entries are dropped; fewer than ``MIN_SUGGESTED_COMPETENCIES``
    surviving entries is a failed pass (callers fall back to deterministic).
    """
    items = data.get("competencies") if isinstance(data, dict) else None
    rationale = str((data or {}).get("rationale") or "").strip()[:600]
    if not isinstance(items, list):
        return [], rationale
    seen: set[str] = set()
    entries: list[dict] = []
    for item in items:
        entry = _normalize_entry(item)
        if entry is None or entry["id"] in seen:
            continue
        seen.add(entry["id"])
        entries.append(entry)
        if len(entries) >= MAX_SUGGESTED_COMPETENCIES:
            break
    return entries, rationale


def _suggest_from_taxonomy(role_context: dict) -> list[dict]:
    """Deterministic fallback — match the role's skills/keywords onto the
    default taxonomy so the engine never proposes an empty set."""
    corpus: list[str] = []
    corpus += [str(s).strip().lower() for s in (role_context.get("skills_required") or []) if str(s).strip()]
    job_role = str(role_context.get("job_role") or "")
    corpus += re.findall(r"[a-z][a-z0-9+#./-]{1,31}", job_role.lower())
    description = str(role_context.get("description") or "").lower()
    corpus += re.findall(r"[a-z][a-z0-9+#./-]{1,31}", description)
    corpus = [c.strip() for c in corpus if c.strip()]

    counts: dict[str, int] = {}
    for token in corpus:
        for skill, cid in SKILL_TO_COMPETENCY.items():
            if skill in token or token in skill:
                counts[cid] = counts.get(cid, 0) + 1

    by_id = {c["id"]: c for c in COMPETENCY_TAXONOMY}
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    picked: list[str] = [cid for cid, _ in ranked if cid in by_id]

    family = detect_family(
        str(role_context.get("job_role") or ""),
        str(role_context.get("description") or ""),
    )
    anchors = _FAMILY_FALLBACKS.get(family, _TECH_FAMILY_FALLBACK)
    for fallback_id in anchors + _UNIVERSAL_FALLBACK + ("tech_core",):
        if len(picked) >= MIN_SUGGESTED_COMPETENCIES:
            break
        if fallback_id not in picked and fallback_id in by_id:
            picked.append(fallback_id)

    entries = []
    for cid in picked[:MAX_SUGGESTED_COMPETENCIES]:
        meta = by_id[cid]
        count = counts.get(cid, 1)
        entries.append(
            {
                **meta,
                "weight": round(min(3.0, 1.0 + 0.5 * count), 2),
                "max_score": 10.0,
                "verification_probe": (
                    f"Ask the candidate to demonstrate {meta['name']} with a "
                    f"concrete, quantified example"
                ),
                "skills": [s for s, mapped in SKILL_TO_COMPETENCY.items() if mapped == cid][:6],
            }
        )
    return entries


async def suggest_competencies(
    role_context: dict,
    existing_competencies: list | None = None,
    use_llm: bool = True,
) -> tuple[list[dict] | None, str, str]:
    """Propose competencies for a role.

    Returns ``(entries, source, rationale)``:
        entries  — validated taxonomy entries, or None when the pass failed
        source   — "ai:llm", "ai:deterministic", or "cache:memory"
        rationale — profiler rationale ('' for deterministic)
    """
    key = role_cache_key(role_context)
    cached = _SUGGESTION_CACHE.get(key)
    if cached is not None:
        _SUGGESTION_CACHE.move_to_end(key)
        return list(cached["entries"]), "cache:memory", cached.get("rationale", "")

    if not use_llm:
        entries = _suggest_from_taxonomy(role_context)
        _cache_put(key, entries, "ai:deterministic", "")
        return entries, "ai:deterministic", ""

    try:
        from app.intelligence._helpers import parse_llm_json_with_retry
        from app.services.llm_service import get_llm_service
        from app.services.prompt_loader import load_prompt

        prompt = load_prompt(
            "intelligence",
            "role_competency_profiler.md",
            job_role=role_context.get("job_role", "Unknown"),
            seniority="senior" if "senior" in role_context.get("job_role", "").lower() else "mid-level",
            skills_required=", ".join(role_context.get("skills_required") or []) or "not specified",
            description=role_context.get("description") or "not specified",
            department_name=role_context.get("department_name") or "not specified",
            org_name=role_context.get("org_name") or "not specified",
            tech_stack=", ".join(role_context.get("tech_stack") or []) or "not specified",
            existing_competencies=(
                json.dumps(existing_competencies, indent=2)[:2000]
                if existing_competencies
                else ""
            ),
        )
        data = await parse_llm_json_with_retry(
            get_llm_service(), prompt, temperature=0.0, max_tokens=900, tier="cheap"
        )
        entries, rationale = _validate_suggestions(data)
        if len(entries) < MIN_SUGGESTED_COMPETENCIES:
            logger.warning(
                "Role profiler LLM pass invalid (%d competencies), using deterministic",
                len(entries),
            )
            entries = _suggest_from_taxonomy(role_context)
            _cache_put(key, entries, "ai:deterministic", "")
            return entries, "ai:deterministic", ""
        _cache_put(key, entries, "ai:llm", rationale)
        return entries, "ai:llm", rationale
    except Exception as exc:  # noqa: BLE001 - profiler is best-effort
        logger.warning("Role profiler LLM failed (%s), using deterministic", exc)
        entries = _suggest_from_taxonomy(role_context)
        _cache_put(key, entries, "ai:deterministic", "")
        return entries, "ai:deterministic", ""


def _cache_put(key: str, entries: list[dict], source: str, rationale: str) -> None:
    _SUGGESTION_CACHE[key] = {"entries": entries, "source": source, "rationale": rationale}
    _SUGGESTION_CACHE.move_to_end(key)
    while len(_SUGGESTION_CACHE) > _MAX_CACHE_ENTRIES:
        _SUGGESTION_CACHE.popitem(last=False)
