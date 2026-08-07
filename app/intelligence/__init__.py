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
    competency_taxonomy: list | None = None,
    use_rag: bool = True,
    use_llm: bool = True,
    company_brain: dict | None = None,
) -> dict:
    """One-shot V5 intelligence bundle for ``InterviewEngine.start_session``.

    Pipeline order (F1, role-first):
        1. company_brain      — org/dept context (RAG + LLM, cached)
        2. competency set     — resolved by the caller (scorecard → template →
                               AI role profiler → default) and passed in as
                               ``competency_taxonomy``/``required_competencies``
        3. interview_blueprint — the competency set is FIXED by the role; company
                               context only grounds the scenario material
        4. evidence_requirements — per-competency probes (verification_probe)
        5. candidate intelligence + hypotheses

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

    blueprint = await build_interview_blueprint(
        job_role=job_role,
        company_brain=company_brain,
        style=style,
        required_competencies=required_competencies,
        competency_taxonomy=competency_taxonomy,
        use_llm=use_llm,
    )

    evidence_requirements = resolve_evidence_requirements(
        scorecard_competencies or competency_taxonomy,
        taxonomy=competency_taxonomy,
        max_requirements=12,
    )

    candidate = await build_candidate_intelligence(
        job_role=job_role,
        candidate_id=candidate_id,
        candidate_profile=candidate_profile,
        resume_text=resume_text,
        required_competencies=required_competencies,
        competency_taxonomy=competency_taxonomy,
        use_llm=use_llm and bool(resume_text),
    )

    aura_brain = _build_pre_interview_brain(
        job_role=job_role,
        company_brain=company_brain,
        taxonomy=competency_taxonomy,
        required_competencies=required_competencies,
        candidate_bundle=candidate,
        candidate_id=candidate_id,
    )

    return {
        "company_brain": company_brain,
        "interview_blueprint": blueprint,
        "evidence_requirements": evidence_requirements,
        **candidate,  # candidate_brain, initial_hypotheses, candidate_assessment
        "aura_brain": aura_brain,
    }


def _build_pre_interview_brain(
    *,
    job_role: str,
    company_brain: dict | None,
    taxonomy: list | None,
    required_competencies: list[str] | None,
    candidate_bundle: dict,
    candidate_id: str,
) -> dict:
    """Assemble the V5 brain before any interview turn (pre-interview state).

    Company + role + competency-graph + hypotheses + first question strategy.
    Evidence layers start empty; they grow with each answer.
    """
    from app.brain.assembler import assemble_aura_brain

    try:
        return assemble_aura_brain(
            job_role=job_role,
            company_brain=company_brain,
            taxonomy=taxonomy,
            required_competencies=required_competencies,
            candidate_brain=candidate_bundle.get("candidate_brain"),
            candidate_assessment=candidate_bundle.get("candidate_assessment"),
            candidate_id=candidate_id,
            hypotheses=candidate_bundle.get("initial_hypotheses"),
            evidence_store=[],
            competency_summary={},
            contradictions=[],
            difficulty_reached=1,
            role_floor=None,
        )
    except Exception as exc:  # noqa: BLE001 - brain assembly is best-effort
        logger.warning(f"Pre-interview AURA brain assembly failed (non-fatal): {exc}")
        return {}
