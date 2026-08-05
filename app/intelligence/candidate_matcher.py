"""Candidate matcher — deterministic skill-to-role matching.

Produces the match score, competency coverage, gaps and recommended probes
that feed ``candidate_assessment`` and the engine's hypothesis seeding.
Fully offline and deterministic.
"""
import logging
import re

from app.data.competency_taxonomy import COMPETENCY_TAXONOMY, SKILL_TO_COMPETENCY

logger = logging.getLogger(__name__)


def match_candidate_to_role(
    *,
    skills: list[str],
    job_role: str = "",
    required_competencies: list[str] | None = None,
) -> dict:
    """Score how well a candidate's skills cover the role's competencies.

    Returns:
        dict with match_score (0..1), signal_strength, matched_skills, gaps,
        recommended_probes, competency_coverage.
    """
    skills = [s.lower().strip() for s in (skills or [])]
    matched_skills = [s for s in skills if s in SKILL_TO_COMPETENCY]
    matched_comps = {SKILL_TO_COMPETENCY[s] for s in matched_skills}

    req_comp = required_competencies or [c["id"] for c in COMPETENCY_TAXONOMY]
    covered = [c for c in req_comp if c in matched_comps]
    gaps = [c for c in req_comp if c not in matched_comps]

    role_kws = re.findall(r"\w+", (job_role or "").lower())
    role_skill_hits = [kw for kw in role_kws if kw in SKILL_TO_COMPETENCY and kw in skills]

    score = 0.4
    if req_comp:
        score += 0.5 * (len(covered) / len(req_comp))
    if role_skill_hits:
        score = min(score + 0.1, 0.95)
    score = round(max(0.1, min(1.0, score)), 4)

    if score >= 0.8:
        signal = "strong"
    elif score >= 0.5:
        signal = "moderate"
    else:
        signal = "weak"

    probes = [
        {
            "competency": cid,
            "probe": f"Verify evidence of {cid.replace('_', ' ')} through a concrete scenario",
        }
        for cid in gaps[:4]
    ]

    return {
        "match_score": score,
        "signal_strength": signal,
        "matched_skills": matched_skills,
        "gaps": gaps,
        "recommended_probes": probes,
        "competency_coverage": covered,
    }


def risk_signals(candidate_brain: dict) -> list[str]:
    """Heuristic risk signals from the candidate brain."""
    signals = []
    years = candidate_brain.get("years_of_experience")
    if years is not None and years < 1:
        signals.append("Limited professional experience")
    if not candidate_brain.get("skills"):
        signals.append("No skills detected in resume/profile")
    if not candidate_brain.get("strengths"):
        signals.append("No clear strengths identified yet")
    if candidate_brain.get("source") == "profile" and not candidate_brain.get("headline"):
        signals.append("Thin candidate profile — resume enrichment recommended")
    return signals
