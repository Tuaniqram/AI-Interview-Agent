"""Automatic application fit evaluation.

After a candidate applies, an LLM compares their CV with the listing, the IT
role's competencies (``role_competencies``) and the organization's own
documents (org-scoped RAG), and produces ``fit_score`` (0-10), ``fit_summary``
and a structured ``fit_breakdown``. It never accepts or rejects anyone: the
organization decides whom to invite.

State machine on ``public_interview_submissions.fit_status``::

    pending -> running -> completed | failed

A failed evaluation leaves the application fully usable and can be re-run by
the organization owner.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import (
    CandidateDocument,
    CandidateProfile,
    Competency,
    ItRole,
    Organization,
    PublicInterview,
    PublicInterviewSubmission,
    RoleCompetency,
)

logger = logging.getLogger(__name__)

PROMPT_CATEGORY = "evaluation"
PROMPT_FILE = "application_fit.md"

RESUME_CHARS = 6000
ORG_CONTEXT_CHARS = 4000
LISTING_CHARS = 1500
RETRIEVAL_TIMEOUT_S = 30.0
MAX_ITEMS = 6
MAX_ITEM_CHARS = 400
MAX_ERROR_CHARS = 500


# ── output contract ──────────────────────────────────────────────────────


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


class MatchedCompetency(BaseModel):
    id: str
    evidence: str = ""


class MissingCompetency(BaseModel):
    id: str
    reason: str = ""


class FitResult(BaseModel):
    """Validated LLM output. ``fit_score`` outside 0-10 is rejected, not clamped."""

    fit_score: float = Field(ge=0, le=10)
    fit_summary: str = Field(min_length=1)
    matched_competencies: list[MatchedCompetency] = Field(default_factory=list)
    missing_competencies: list[MissingCompetency] = Field(default_factory=list)
    resume_strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_probes: list[str] = Field(default_factory=list)

    @field_validator("matched_competencies", "missing_competencies", mode="before")
    @classmethod
    def _coerce_competency_items(cls, value):
        # Models sometimes answer ["tech_core"] instead of [{"id": "tech_core"}].
        if not isinstance(value, list):
            return []
        return [{"id": item} if isinstance(item, str) else item for item in value]

    @field_validator("resume_strengths", "risks", "recommended_probes", mode="before")
    @classmethod
    def _coerce_text_items(cls, value):
        return _as_str_list(value)


def validate_fit_result(data: dict, allowed_competency_ids: set[str]) -> FitResult:
    """Validate the LLM JSON and keep it inside the role's competency set.

    Competencies are never invented: ids that are not in the role's mapping are
    dropped. Lists are bounded so a runaway answer cannot bloat the row.
    """
    if not isinstance(data, dict):
        raise ValueError("fit evaluation output is not a JSON object")
    result = FitResult.model_validate(data)

    def _keep(items):
        kept = []
        for item in items:
            if allowed_competency_ids and item.id not in allowed_competency_ids:
                continue
            kept.append(item)
        return kept[:MAX_ITEMS]

    result.matched_competencies = _keep(result.matched_competencies)
    result.missing_competencies = _keep(result.missing_competencies)
    result.fit_summary = result.fit_summary.strip()
    result.fit_score = round(result.fit_score, 1)
    for name in ("resume_strengths", "risks", "recommended_probes"):
        setattr(result, name, [t[:MAX_ITEM_CHARS] for t in getattr(result, name)][:MAX_ITEMS])
    return result


# ── prompt inputs ────────────────────────────────────────────────────────

_BRACES = re.compile(r"\{\{|\}\}")


def _neutralize(text: str) -> str:
    """Candidate/org text is untrusted. PromptLoader substitutes ``{{key}}``
    sequentially, so break any braces that could be re-expanded."""
    return _BRACES.sub(lambda m: "{ {" if m.group(0) == "{{" else "} }", text or "")


def _format_competencies(competencies: list[dict]) -> str:
    if not competencies:
        return "(no competency mapping for this role; judge general fit for the role title)"
    lines = []
    for c in competencies:
        weight = c.get("weight")
        lines.append(
            " | ".join(
                [
                    str(c["id"]),
                    str(c.get("name") or c["id"]),
                    f"{float(weight):g}" if weight is not None else "1",
                    "core" if c.get("is_core") else "supporting",
                    str(c.get("required_level") or "-"),
                ]
            )
        )
    return "\n".join(lines)


def _format_match(match: dict) -> str:
    return (
        f"keyword match score: {match.get('match_score', 0):.2f} ({match.get('signal_strength', 'weak')})\n"
        f"skills recognised: {', '.join(match.get('matched_skills') or []) or 'none'}\n"
        f"competencies covered by keywords: {', '.join(match.get('competency_coverage') or []) or 'none'}\n"
        f"competencies with no keyword evidence: {', '.join(match.get('gaps') or []) or 'none'}"
    )


def _format_profile(analysis: dict) -> str:
    parts = [
        f"headline: {analysis.get('headline') or '-'}",
        f"years of experience: {analysis.get('years_of_experience') or 'unknown'}",
        f"skills: {', '.join(analysis.get('skills') or []) or '-'}",
    ]
    return "\n".join(parts)


def build_prompt_inputs(
    *,
    ctx: dict,
    analysis: dict,
    match: dict,
    org_context: str,
) -> dict[str, str]:
    """Variables for ``prompts/evaluation/application_fit.md``."""
    return {
        "job_role": _neutralize(ctx["title"]),
        "level": _neutralize(ctx.get("level_code") or ctx.get("role_name") or "not specified"),
        "skills_required": _neutralize(ctx.get("skills_required") or "not specified"),
        "organization_name": _neutralize(ctx.get("org_name") or "the organization"),
        "listing_description": _neutralize((ctx.get("description") or "not provided")[:LISTING_CHARS]),
        "role_competencies": _format_competencies(ctx["competencies"]),
        "deterministic_match": _format_match(match),
        "organization_context": _neutralize(org_context) if org_context else "(none available)",
        "candidate_profile": _neutralize(_format_profile(analysis)),
        "resume_text": _neutralize(ctx["resume_text"][:RESUME_CHARS]),
    }


# ── data access ──────────────────────────────────────────────────────────


async def _load_context(db: AsyncSession, application_id: UUID) -> dict:
    """Everything the evaluation needs, as plain data (no ORM objects), so the
    DB transaction can be released before the slow RAG/LLM calls."""
    submission = await db.get(PublicInterviewSubmission, application_id)
    if submission is None:
        raise LookupError("application not found")

    pi = await db.get(PublicInterview, submission.public_id)
    if pi is None:
        raise LookupError("listing not found")
    org = await db.get(Organization, pi.org_id)
    role = await db.get(ItRole, pi.it_role_id) if pi.it_role_id else None

    competencies: list[dict] = []
    if pi.it_role_id:
        rows = (
            await db.execute(
                select(RoleCompetency, Competency)
                .join(Competency, Competency.id == RoleCompetency.competency_id)
                .where(RoleCompetency.role_id == pi.it_role_id, Competency.is_active.is_(True))
                .order_by(RoleCompetency.is_core.desc(), RoleCompetency.weight.desc())
            )
        ).all()
        competencies = [
            {
                "id": comp.id,
                "name": comp.name,
                "weight": float(rc.weight) if rc.weight is not None else 1.0,
                "is_core": bool(rc.is_core),
                "required_level": rc.required_level,
            }
            for rc, comp in rows
        ]

    document = None
    if submission.resume_document_id:
        document = await db.get(CandidateDocument, submission.resume_document_id)
    profile = (
        await db.get(CandidateProfile, submission.candidate_profile_id)
        if submission.candidate_profile_id
        else None
    )

    return {
        "application_id": str(submission.id),
        "org_id": str(pi.org_id),
        "org_name": org.name if org else None,
        "title": pi.title,
        "description": pi.description or pi.rich_description,
        "skills_required": pi.skills_required,
        "level_code": pi.level_code,
        "role_name": role.name if role else None,
        "competencies": competencies,
        "candidate_name": submission.candidate_name,
        "profile_skills": [s.strip() for s in (profile.skills or "").split(",") if s.strip()] if profile else [],
        "resume_text": (document.extracted_text or "").strip() if document else "",
        "resume_filename": document.filename if document else None,
    }


async def _retrieve_org_context(org_id: str, query: str) -> tuple[str, int, Optional[str]]:
    """Org-scoped RAG. Best effort: returns (text, documents, error)."""
    try:
        from app.rag.pinecone_store import get_org_retriever

        def _retrieve():
            return get_org_retriever(org_id).invoke(query)

        docs = await asyncio.wait_for(asyncio.to_thread(_retrieve), timeout=RETRIEVAL_TIMEOUT_S)
        text = "\n\n".join(d.page_content for d in docs if getattr(d, "page_content", ""))
        return text[:ORG_CONTEXT_CHARS], len(docs), None
    except Exception as exc:  # noqa: BLE001 - org docs enrich the evaluation, they are not required
        logger.warning("Org RAG retrieval failed for org %s: %s", org_id, exc)
        return "", 0, str(exc)[:MAX_ERROR_CHARS]


async def _call_llm(prompt: str) -> dict:
    from app.intelligence._helpers import parse_llm_json_with_retry
    from app.services.llm_service import get_llm_service

    return await parse_llm_json_with_retry(
        get_llm_service(), prompt, temperature=0.2, max_tokens=1200, tier="strong"
    )


# ── orchestration ────────────────────────────────────────────────────────


async def _mark(
    db: AsyncSession, application_id: UUID, *, fit_status: str, error: Optional[str] = None
) -> None:
    row = await db.get(PublicInterviewSubmission, application_id)
    if row is None:
        return
    row.fit_status = fit_status
    row.fit_error = error
    await db.commit()


async def evaluate_application_fit(
    application_id: UUID | str, db: AsyncSession
) -> Optional[PublicInterviewSubmission]:
    """Evaluate one application and persist the result. Never raises for
    evaluation problems: they become ``fit_status = 'failed'`` + ``fit_error``.
    Returns the refreshed submission (``None`` if it does not exist)."""
    application_id = UUID(str(application_id))
    if await db.get(PublicInterviewSubmission, application_id) is None:
        return None

    try:
        await _mark(db, application_id, fit_status="running")
        ctx = await _load_context(db, application_id)
        await db.commit()  # release the connection before the slow RAG/LLM calls

        if not ctx["resume_text"]:
            raise ValueError(
                "The CV has no readable text (scanned or image-only PDF); ask for a text-based PDF."
            )

        from app.intelligence.candidate_matcher import match_candidate_to_role
        from app.intelligence.resume_analyzer import analyze_resume
        from app.services.prompt_loader import load_prompt

        analysis = await analyze_resume(
            ctx["resume_text"],
            ctx["title"],
            candidate_profile={"full_name": ctx["candidate_name"], "skills": ctx["profile_skills"]},
        )
        competency_ids = {c["id"] for c in ctx["competencies"]}
        match = match_candidate_to_role(
            skills=analysis.get("skills") or [],
            job_role=ctx["title"],
            required_competencies=[c["id"] for c in ctx["competencies"]] or None,
        )
        org_text, org_docs, rag_error = await _retrieve_org_context(
            ctx["org_id"],
            f"{ctx['title']} requirements, technical stack, team practices, "
            f"engineering culture, what we look for in candidates",
        )

        prompt = load_prompt(
            PROMPT_CATEGORY,
            PROMPT_FILE,
            **build_prompt_inputs(ctx=ctx, analysis=analysis, match=match, org_context=org_text),
        )
        result = validate_fit_result(await _call_llm(prompt), competency_ids)

        names = {c["id"]: c.get("name") or c["id"] for c in ctx["competencies"]}
        breakdown = {
            "matched_competencies": [
                {**m.model_dump(), "name": names.get(m.id, m.id)} for m in result.matched_competencies
            ],
            "missing_competencies": [
                {**m.model_dump(), "name": names.get(m.id, m.id)} for m in result.missing_competencies
            ],
            "resume_strengths": result.resume_strengths,
            "risks": result.risks,
            "recommended_probes": result.recommended_probes,
            "meta": {
                "competency_source": "role_competencies" if competency_ids else "none",
                "competencies_considered": len(competency_ids),
                "org_documents_used": org_docs,
                "org_context_error": rag_error,
                "resume_chars": len(ctx["resume_text"]),
                "resume_filename": ctx["resume_filename"],
                "keyword_match_score": match.get("match_score"),
                "resume_analysis_source": analysis.get("source"),
            },
        }

        row = await db.get(PublicInterviewSubmission, application_id)
        if row is None:  # deleted while evaluating
            return None
        row.fit_score = result.fit_score
        row.fit_summary = result.fit_summary
        row.fit_breakdown = breakdown
        row.fit_status = "completed"
        row.fit_error = None
        row.fit_evaluated_at = datetime.now(timezone.utc)
        if row.status == "applied":
            row.status = "evaluated"
        await db.commit()
        await db.refresh(row)
        return row

    except Exception as exc:  # noqa: BLE001 - keep the application usable, allow org re-run
        logger.exception("Application fit evaluation failed for %s", application_id)
        message = (
            "; ".join(e["msg"] for e in exc.errors()[:3]) if isinstance(exc, ValidationError) else str(exc)
        )
        try:
            await db.rollback()
            await _mark(db, application_id, fit_status="failed", error=message[:MAX_ERROR_CHARS])
        except Exception:  # noqa: BLE001
            logger.exception("Could not record fit evaluation failure for %s", application_id)
        return await db.get(PublicInterviewSubmission, application_id)


async def run_application_fit_evaluation(application_id: str) -> None:
    """Background-task entry point: owns its DB session because the request's
    session is closed by the time background tasks run."""
    from app.database.session import get_session_factory

    factory = get_session_factory()
    if factory is None:
        logger.error("Fit evaluation skipped for %s: database is not configured", application_id)
        return
    try:
        async with factory() as db:
            await evaluate_application_fit(application_id, db)
    except Exception:  # noqa: BLE001 - a background task must never raise
        logger.exception("Background fit evaluation crashed for %s", application_id)


async def resume_unfinished_evaluations(limit: int = 50) -> int:
    """Re-run evaluations a previous process left unfinished.

    Evaluations run as in-process background tasks, so a restart or redeploy in the middle of one
    leaves the application ``pending`` / ``running`` forever (until someone presses Re-run). Called
    once at startup; runs them one at a time so a backlog does not flood the LLM provider.
    """
    from app.database.session import get_session_factory

    factory = get_session_factory()
    if factory is None:
        return 0
    try:
        async with factory() as db:
            ids = (
                await db.execute(
                    select(PublicInterviewSubmission.id)
                    .where(
                        PublicInterviewSubmission.fit_status.in_(("pending", "running")),
                        PublicInterviewSubmission.resume_document_id.is_not(None),
                    )
                    .order_by(PublicInterviewSubmission.created_at)
                    .limit(limit)
                )
            ).scalars().all()
    except Exception:  # noqa: BLE001 - startup recovery is best-effort
        logger.exception("Could not look up unfinished fit evaluations")
        return 0
    if ids:
        logger.info("Resuming %d unfinished fit evaluation(s)", len(ids))
    for application_id in ids:
        await run_application_fit_evaluation(str(application_id))
    return len(ids)
