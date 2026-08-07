"""Scorecard resolver — turns scorecard template competencies into the
``evidence_requirements`` the engine uses to drive coverage.

Deterministic and fully offline: it maps scorecard entries onto the static
competency taxonomy and never calls the LLM.
"""
import logging

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY

logger = logging.getLogger(__name__)

DEFAULT_MAX_REQUIREMENTS = 12

_DEFAULT_PROBES = {
    "tech_core": "Ask for a live coding example demonstrating core language mastery",
    "tech_framework": "Ask for a concrete feature built with the relevant framework",
    "tech_system_design": "Walk through designing a system end-to-end, probing trade-offs",
    "tech_data": "Ask for an algorithm/data-structure problem solved with reasoning",
    "tech_db": "Ask about schema design, indexing strategy, and a tricky query",
    "tech_devops": "Ask about a deployment pipeline, incident response, or CI/CD setup",
    "tech_testing": "Ask how testing is layered and how a flaky test is chased down",
    "tech_security": "Ask how security is handled in auth, input handling, or infra",
    "behav_teamwork": "Ask for a story of cross-team collaboration and conflict resolution",
    "behav_leadership": "Ask for ownership of a project with ambiguity and accountability",
    "behav_conflict": "Ask for a real conflict, how it escalated, and how it was resolved",
    "behav_communication": "Ask how a complex technical idea was explained to a non-technical audience",
    "behav_adaptability": "Ask for a time the candidate had to learn a new stack quickly",
    "cog_problem_solving": "Ask for an unstructured problem solved with a clear process",
    "cog_analytical": "Ask how a decision was made from incomplete data",
    "cog_creativity": "Ask for an innovative or unconventional solution the candidate drove",
    "cog_decision_making": "Ask for a high-stakes decision with competing trade-offs",
    "exp_project_depth": "Ask for the deepest, highest-impact project and the candidate's role",
    "exp_domain": "Ask how domain knowledge shaped a design or business outcome",
    "exp_scaling": "Ask about scale/performance challenges and their resolution",
    "exp_best_practices": "Ask how engineering standards and code quality are upheld",
}


def resolve_evidence_requirements(
    competencies: list | None = None,
    taxonomy: list | None = None,
    max_requirements: int = DEFAULT_MAX_REQUIREMENTS,
) -> list[dict]:
    """Map scorecard competencies onto the taxonomy as evidence requirements.

    Args:
        competencies: list of ``{"id"|"competency": str, "name": str, "weight": float}``
            from a scorecard template. ``None``/empty means "use the full taxonomy".
        taxonomy: overridable taxonomy (defaults to the static one).
        max_requirements: cap on the number of requirements returned.

    Returns:
        list of requirement dicts with competency/name/min_evidence/dimensions/
        weight/verification_probe.
    """
    taxonomy = taxonomy or COMPETENCY_TAXONOMY
    by_id = {c["id"]: c for c in taxonomy}

    requirements = []
    seen = set()

    def _requirement(cid: str, name: str, weight: float) -> dict:
        meta = by_id.get(cid, {})
        return {
            "competency": cid,
            "name": name or meta.get("name", cid),
            "min_evidence": meta.get("default_min_evidence", 2),
            "dimensions": meta.get("evidence_dimensions", ["technical", "completeness"]),
            "weight": round(float(weight), 4) if weight is not None else 1.0,
            "verification_probe": meta.get("verification_probe")
            or _DEFAULT_PROBES.get(cid, f"Probe for evidence of {cid}"),
            "skills": meta.get("skills") or [],
        }

    if competencies:
        for comp in competencies:
            cid = None
            if isinstance(comp, dict):
                cid = comp.get("id") or comp.get("competency")
                weight = comp.get("weight", 1.0)
                name = comp.get("name", "")
            else:
                cid = comp
                weight = 1.0
                name = ""
            if not cid or cid in seen:
                continue
            seen.add(cid)
            requirements.append(_requirement(cid, name, weight))
    else:
        for meta in taxonomy:
            requirements.append(_requirement(meta["id"], meta["name"], 1.0))

    return requirements[:max_requirements]
