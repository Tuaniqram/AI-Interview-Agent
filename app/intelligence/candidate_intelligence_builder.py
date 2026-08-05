"""Candidate intelligence builder — candidate_brain + initial_hypotheses +
candidate_assessment for engine injection.

The initial hypotheses reuse the deterministic hypothesis manager (seeded from
resume/profile strengths and weaknesses) so the evidence engine has a coherent
prior the moment a session starts. Bayesian ``probability`` is attached for the
V5 hypothesis upgrades.
"""
import logging

logger = logging.getLogger(__name__)


async def build_candidate_intelligence(
    *,
    job_role: str,
    candidate_id: str = "",
    candidate_profile: dict | None = None,
    resume_text: str | None = None,
    required_competencies: list[str] | None = None,
    use_llm: bool = True,
) -> dict:
    """Build the candidate-side intelligence bundle.

    Returns:
        dict with ``candidate_brain``, ``initial_hypotheses`` and
        ``candidate_assessment``.
    """
    from app.agents.reasoning.hypothesis_engine import generate_initial_hypotheses
    from app.intelligence.candidate_matcher import match_candidate_to_role, risk_signals
    from app.intelligence.resume_analyzer import analyze_resume

    brain_data = await analyze_resume(
        resume_text or "",
        job_role=job_role,
        candidate_profile=candidate_profile,
        use_llm=use_llm,
    )
    brain_data["candidate_id"] = candidate_id
    brain_data["job_role"] = job_role

    hypotheses = generate_initial_hypotheses(
        job_role,
        {
            "strengths": brain_data.get("strengths", []),
            "weaknesses": brain_data.get("weaknesses", []),
        },
        competency_taxonomy=None,
    )
    for h in hypotheses:
        h["probability"] = float(h.get("confidence", 0.5))
        h["evidence_based"] = False
        h["source"] = "resume_profile"

    match = match_candidate_to_role(
        skills=brain_data.get("skills", []),
        job_role=job_role,
        required_competencies=required_competencies,
    )

    assessment = {
        "version": "v1",
        "match_score": match["match_score"],
        "signal_strength": match["signal_strength"],
        "strong_areas": match["matched_skills"],
        "gap_areas": match["gaps"],
        "competency_coverage": match["competency_coverage"],
        "recommended_probes": match["recommended_probes"],
        "risk_signals": risk_signals(brain_data),
    }

    return {
        "candidate_brain": brain_data,
        "initial_hypotheses": hypotheses,
        "candidate_assessment": assessment,
    }
