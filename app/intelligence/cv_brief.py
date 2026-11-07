"""CV brief - a short, prompt-ready summary of what the candidate's CV says.

The question writer uses it so the interview can start from the candidate's real projects instead of
a generic scenario. Everything in it is an UNVERIFIED claim from the CV (or a suggested probe from
the application fit evaluation); the prompt tells the model to treat it as data and to verify it,
never to assume it is true and never to mention the fit evaluation to the candidate.
"""
import re

_WS = re.compile(r"\s+")


def _clip(value: object, limit: int) -> str:
    text = _WS.sub(" ", str(value or "")).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _items(value: object, count: int, each: int) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    for item in value:
        text = _clip(item if not isinstance(item, dict) else item.get("summary") or item.get("title") or item, each)
        if text and text not in out:
            out.append(text)
        if len(out) >= count:
            break
    return out


def build_cv_brief(
    candidate_brain: dict | None,
    resume_text: str | None = None,
    fit: dict | None = None,
    max_chars: int = 900,
) -> str:
    """Compact CV summary: headline/years, experience, skills and fit probes. ``""`` when empty."""
    brain = candidate_brain or {}
    lines: list[str] = []

    headline = _clip(brain.get("headline"), 120)
    years = brain.get("years_of_experience")
    if headline or years:
        lines.append("Profile: " + ", ".join(p for p in (headline, f"~{years} yrs experience" if years else "") if p))

    experience = _items(brain.get("experience"), 5, 180)
    if experience:
        lines.append("Experience: " + " | ".join(experience))
    elif resume_text and resume_text.strip():
        lines.append("CV excerpt: " + _clip(resume_text, 600))

    skills = _items(brain.get("skills"), 12, 30)
    if skills:
        lines.append("Skills: " + ", ".join(skills))

    probes = _items((fit or {}).get("recommended_probes"), 3, 160)
    if probes:
        lines.append("Worth probing: " + " | ".join(probes))

    brief = "\n".join(lines)
    return brief if len(brief) <= max_chars else brief[: max_chars - 1].rstrip() + "…"
