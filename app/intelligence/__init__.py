"""V5 Intelligence module — company + candidate intelligence for sessions.

The public entry point is :func:`build_interview_intelligence`, which produces
the exact keyword bundle ``InterviewEngine.start_session`` accepts:

    ``company_brain``, ``interview_blueprint``, ``candidate_brain``,
    ``initial_hypotheses``, ``evidence_requirements``, ``candidate_assessment``

Every stage is best-effort: RAG/LLM failures degrade to deterministic
fallbacks so a session can always start.
"""
import logging

logger = logging.getLogger(__name__)

from app.intelligence.candidate_intelligence_builder import (  # noqa: E402
    build_candidate_intelligence,
)
from app.intelligence.candidate_matcher import match_candidate_to_role, risk_signals  # noqa: E402
from app.intelligence.company_intelligence_builder import build_company_brain  # noqa: E402
from app.intelligence.document_analyzer import analyze_documents  # noqa: E402
from app.intelligence.interview_blueprint_builder import (  # noqa: E402
    build_interview_blueprint,
)
from app.intelligence.resume_analyzer import analyze_resume  # noqa: E402
from app.intelligence.scorecard_resolver import resolve_evidence_requirements  # noqa: E402

__all__ = [
    "build_interview_intelligence",
    "build_company_brain",
    "build_interview_blueprint",
    "build_candidate_intelligence",
    "resolve_evidence_requirements",
    "analyze_documents",
    "analyze_resume",
    "match_candidate_to_role",
    "risk_signals",
]


async def build_interview_intelligence(
    *,
    job_role: str,
    department_id: int | None = None,
    style: dict | None = None,
    candidate_profile: dict | None = None,
    candidate_id: str = "",
    resume_text: str | None = None,
    required_competencies: list[str] | None = None,
    scorecard_competencies: list | None = None,
    use_rag: bool = True,
    use_llm: bool = True,
    company_brain: dict | None = None,
) -> dict:
    """One-shot V5 intelligence bundle for ``InterviewEngine.start_session``.

    All arguments are optional except ``job_role``; missing source material
    yields minimal-but-valid artifacts (no LLM or RAG calls are made when there
    is nothing to analyze). ``company_brain`` may be supplied pre-built (e.g.
    from the department/role cache) to skip the RAG/LLM pass.
    """
    if company_brain is None:
        company_brain = await build_company_brain(
            department_id=department_id,
            job_role=job_role,
            use_rag=use_rag,
            use_llm=use_llm,
        )

    evidence_requirements = resolve_evidence_requirements(
        scorecard_competencies,
        max_requirements=12,
    )

    blueprint = await build_interview_blueprint(
        job_role=job_role,
        company_brain=company_brain,
        style=style,
        required_competencies=required_competencies,
        use_llm=use_llm,
    )

    candidate = await build_candidate_intelligence(
        job_role=job_role,
        candidate_id=candidate_id,
        candidate_profile=candidate_profile,
        resume_text=resume_text,
        required_competencies=required_competencies,
        use_llm=use_llm and bool(resume_text),
    )

    return {
        "company_brain": company_brain,
        "interview_blueprint": blueprint,
        "evidence_requirements": evidence_requirements,
        **candidate,  # candidate_brain, initial_hypotheses, candidate_assessment
    }
