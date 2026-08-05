"""Resume analyzer — structured extraction from resume text.

Feeds ``candidate_brain``. Deterministic heuristic extraction always works;
the LLM pass (guarded) enriches when available. Existing candidate-profile
data is always merged in so profile-first sessions work offline.
"""
import logging
import re

from app.intelligence._helpers import dedupe

logger = logging.getLogger(__name__)


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
        from app.services.llm_service import get_llm_service
        from app.services.prompt_loader import load_prompt

        prompt = load_prompt(
            "intelligence",
            "resume_analysis.md",
            job_role=job_role or "Unknown",
            resume_text=text[:8000],
        )
        response = await get_llm_service().invoke(
            prompt=prompt, temperature=0.2, max_tokens=800, tier="cheap"
        )
        data = json.loads(response.strip().lstrip("```json").strip().rstrip("```").strip())
        for key in ("skills", "experience", "education", "strengths", "weaknesses"):
            if isinstance(data.get(key), list):
                result[key] = dedupe(data[key])
        for key in ("headline", "full_name"):
            if data.get(key):
                result[key] = data[key]
        if data.get("years_of_experience"):
            result["years_of_experience"] = int(data["years_of_experience"])
        result["source"] = "resume_llm"
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Resume LLM parse failed ({exc}); using heuristics")
        result["source"] = "heuristics"

    return result


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
