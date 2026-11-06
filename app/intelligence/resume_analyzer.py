"""Resume analyzer — structured extraction from resume text.

Feeds ``candidate_brain``. Deterministic heuristic extraction always works;
the LLM pass (guarded) enriches when available. Existing candidate-profile
data is always merged in so profile-first sessions work offline.
"""
import logging
import os
import re

from app.intelligence._helpers import dedupe

logger = logging.getLogger(__name__)

# Safety toggle: which LLM backend enriches resume analysis.
#   RESUME_LLM_BACKEND=dspy   (default) -> app/intelligence/dspy_modules.py
#   RESUME_LLM_BACKEND=legacy           -> prompt_loader + parse_llm_json_with_retry
# Read per-call so a process can flip back without a redeploy.
BACKEND_ENV = "RESUME_LLM_BACKEND"


def _use_dspy_backend() -> bool:
    return os.getenv(BACKEND_ENV, "dspy").strip().lower() != "legacy"


async def analyze_resume(
    resume_text: str,
    job_role: str = "",
    candidate_profile: dict | None = None,
    use_llm: bool = True,
) -> dict:
    """Extract candidate_brain-shaped data from resume text + profile.

    Returns a dict with version/full_name/headline/skills/strengths/weaknesses/
    experience/education/years_of_experience/source.
    """
    profile = dict(candidate_profile or {})
    text = (resume_text or "").strip()
    fallback = _heuristic_parse(text, job_role)

    result = {
        "version": "v1",
        "full_name": profile.get("full_name") or fallback["full_name"] or "Candidate",
        "headline": profile.get("headline") or fallback["headline"] or "",
        "skills": dedupe(list(profile.get("skills", [])) + fallback["skills"]),
        "strengths": dedupe(list(profile.get("strengths", [])) + fallback["strengths"]),
        "weaknesses": dedupe(list(profile.get("weaknesses", [])) + fallback["weaknesses"]),
        "experience": fallback["experience"] or list(profile.get("experience", [])) or [],
        "education": fallback["education"],
        "years_of_experience": (
            profile.get("years_of_experience") or fallback["years_of_experience"]
        ),
        "source": "profile",
    }

    if not text:
        result["source"] = "profile"
        return result

    if not use_llm:
        result["source"] = "heuristics"
        return result

    try:
        if _use_dspy_backend():
            from app.intelligence.dspy_modules import run_resume_analysis

            data = await run_resume_analysis(text, job_role)
        else:
            data = await _legacy_llm_parse(text, job_role)
        for key in ("skills", "experience", "education", "strengths", "weaknesses"):
            if isinstance(data.get(key), list):
                result[key] = dedupe(data[key])
        for key in ("headline", "full_name"):
            if data.get(key):
                result[key] = data[key]
        if data.get("years_of_experience"):
            years = _coerce_years(data["years_of_experience"])
            if years is not None:
                result["years_of_experience"] = years
        result["source"] = "resume_llm"
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Resume LLM parse failed ({exc}); using heuristics")
        result["source"] = "heuristics"

    return result


def _coerce_years(value) -> int | None:
    """The LLM often answers ``'N/A'``, ``'8+ years'`` or ``'5-7'`` — extract
    the first integer instead of crashing the whole parse on a bad value."""
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


async def _legacy_llm_parse(text: str, job_role: str) -> dict:
    """Legacy LLM enrichment: prompt_loader + parse_llm_json_with_retry.

    Kept intact as the ``RESUME_LLM_BACKEND=legacy`` escape hatch. Raises on
    failure — callers fall back to heuristics exactly as before.
    """
    from app.intelligence._helpers import parse_llm_json_with_retry
    from app.services.llm_service import get_llm_service
    from app.services.prompt_loader import load_prompt

    prompt = load_prompt(
        "intelligence",
        "resume_analysis.md",
        job_role=job_role or "Unknown",
        resume_text=text[:8000],
    )
    return await parse_llm_json_with_retry(
        get_llm_service(), prompt, temperature=0.2, max_tokens=1000, tier="cheap"
    )


def _heuristic_parse(text: str, job_role: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lowered = text.lower()

    from app.data.competency_taxonomy import SKILL_TO_COMPETENCY

    matched = [kw for kw in SKILL_TO_COMPETENCY if kw in lowered]
    skills = matched[:12]
    strengths = skills[:5]

    weaknesses = []
    role_kws = re.findall(r"\w+", (job_role or "").lower())
    for kw in role_kws:
        if len(kw) > 3 and kw not in lowered:
            weaknesses.append(f"Limited exposure to {kw}")

    years = None
    m = re.search(r"(\d+)\s*\+?\s*(?:years|yrs)", lowered)
    if m:
        years = int(m.group(1))

    return {
        "full_name": lines[0][:60] if lines else "Candidate",
        "headline": lines[1][:120] if len(lines) > 1 else "",
        "skills": skills,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "experience": [],
        "education": [],
        "years_of_experience": years,
    }
