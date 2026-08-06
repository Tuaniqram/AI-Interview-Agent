"""Best-effort persistence for V5 intelligence artifacts.

The bundle tables (``company_brains``, ``interview_blueprints``,
``scorecards``, ``candidate_brains``, ``candidate_evidence_requirements``)
were previously only written by ``POST /api/v1/intelligence/build``. This
module exposes the persister so the engine start path can persist the same
bundle it builds in-memory at session start. All writes are best-effort and
never raise — persistence must never break an interview.
"""
import logging
from uuid import UUID

from sqlalchemy import select

from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


def _dedupe_competencies(items: list) -> list:
    """Dedupe scorecard competencies by id/competency, preserving order."""
    seen, out = set(), []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        key = it.get("id") or it.get("competency") or ""
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _infer_seniority(cand: dict) -> str | None:
    """Derive a seniority label from the experience list when the bundle lacks one."""
    experience = cand.get("experience") or cand.get("work_history") or []
    if not experience:
        return None
    total_years = 0.0
    for role in experience:
        if not isinstance(role, dict):
            continue
        duration = role.get("duration") or role.get("years")
        try:
            total_years += float(str(duration).split()[0]) if duration else 0.0
        except (TypeError, ValueError):
            total_years += 0.0
    if total_years >= 8:
        return "senior"
    if len(experience) >= 3 or total_years >= 5:
        return "mid"
    return "junior"


async def persist_intelligence_bundle(
    session_id,
    department_id: int | None,
    job_role: str,
    bundle: dict,
    db=None,
) -> dict:
    """Best-effort persist of the bundle into the V5 tables.

    ``db`` may be an injected session (API handlers); when ``None`` a fresh
    session is opened via the session factory (engine start path). Returns
    the per-artifact saved flags (``{"company_brain": bool, ...}``). Never
    raises; failures are logged and swallowed.
    """
    saved = {
        "company_brain": False,
        "scorecard": False,
        "blueprint": False,
        "candidate_brain": False,
        "evidence_requirements": False,
    }
    try:
        sid = UUID(str(session_id))
    except (ValueError, TypeError, AttributeError):
        logger.warning(
            f"V5 intelligence persistence skipped: invalid session_id {session_id!r}"
        )
        return saved

    owns_session = db is None
    if owns_session:
        factory = get_session_factory()
        if factory is None:
            return saved
        db = factory()

    try:
        from app.models.db import (
            CandidateBrain,
            CandidateEvidenceRequirement,
            CompanyBrain,
            InterviewBlueprint,
            InterviewSession,
            Scorecard,
        )

        existing = {
            "company_brain": await _has_row(db, CompanyBrain, sid),
            "blueprint": await _has_row(db, InterviewBlueprint, sid),
            "scorecard": await _has_row(db, Scorecard, sid),
            "candidate_brain": await _has_row(db, CandidateBrain, sid),
            "evidence_requirements": await _has_row(db, CandidateEvidenceRequirement, sid),
        }

        cb = bundle.get("company_brain") or {}
        if not existing["company_brain"]:
            db.add(CompanyBrain(
                session_id=sid,
                department_id=department_id,
                company_name=cb.get("company_name") or job_role or "Unknown Company",
                industry=cb.get("industry"),
                company_vision=cb.get("company_vision") or cb.get("mission"),
                values=cb.get("values") or [],
                technical_stack=cb.get("technical_stack") or cb.get("tech_stack") or [],
                culture=cb.get("culture") or [],
                success_signals=cb.get("success_signals") or [],
                red_flags=cb.get("red_flags") or [],
                source_documents=cb.get("source_documents") or cb.get("documents_analyzed") or [],
                snapshot=cb,
            ))
        saved["company_brain"] = existing["company_brain"] or True

        blueprint = bundle.get("interview_blueprint") or {}
        priority_competencies = blueprint.get("priority_competencies") or []
        blueprint_objectives = blueprint.get("objectives") or [
            {
                "competency": pc.get("id", ""),
                "name": pc.get("name"),
                "weight": pc.get("weight", 1.0),
            }
            for pc in priority_competencies
        ]
        blueprint_hypothesis_template = blueprint.get("hypothesis_template") or [
            {
                "competency": pc.get("id", ""),
                "statement": f"Candidate demonstrates {pc.get('name') or pc.get('id', '')}",
            }
            for pc in priority_competencies
        ]
        if not existing["blueprint"]:
            db.add(InterviewBlueprint(
                session_id=sid,
                department_id=department_id,
                role=job_role,
                objectives=blueprint_objectives,
                phases=blueprint.get("phases") or [],
                hypothesis_template=blueprint_hypothesis_template,
                evidence_requirements=blueprint.get("evidence_requirements") or [],
                snapshot=blueprint,
            ))
        saved["blueprint"] = existing["blueprint"] or True

        requirements = bundle.get("evidence_requirements") or []
        scorecard_competencies = blueprint.get("scorecard_competencies") or _dedupe_competencies(
            [
                {
                    "id": r.get("competency", ""),
                    "name": r.get("name", ""),
                    "weight": r.get("weight", 1.0),
                }
                for r in requirements
            ]
        )
        if not existing["scorecard"] and scorecard_competencies:
            db.add(Scorecard(
                session_id=sid,
                department_id=department_id,
                role=job_role,
                competencies=scorecard_competencies,
                required_level=blueprint.get("required_level"),
                snapshot=blueprint,
            ))
            saved["scorecard"] = True

        cand = bundle.get("candidate_brain") or {}
        candidate_id = bundle.get("candidate_id") or cand.get("candidate_id")
        if not candidate_id:
            session_row = await db.execute(
                select(InterviewSession.candidate_profile_id).where(
                    InterviewSession.id == sid
                )
            )
            candidate_id = session_row.scalar_one_or_none()
        if not existing["candidate_brain"]:
            db.add(CandidateBrain(
                session_id=sid,
                candidate_id=UUID(str(candidate_id)) if candidate_id else None,
                full_name=(cand.get("full_name") or cand.get("name") or "Unknown Candidate"),
                resume_summary=cand.get("resume_summary") or cand.get("headline"),
                skills=cand.get("skills") or [],
                strengths=cand.get("strengths") or [],
                weaknesses=cand.get("weaknesses") or [],
                work_history=cand.get("work_history") or cand.get("experience"),
                inferred_seniority=cand.get("inferred_seniority") or _infer_seniority(cand),
                persona=cand.get("persona") or {},
                snapshot=cand,
            ))
        saved["candidate_brain"] = existing["candidate_brain"] or True

        if not existing["evidence_requirements"]:
            for req in requirements:
                probes = req.get("required_probes")
                if probes is None:
                    probe = req.get("verification_probe")
                    probes = probe if isinstance(probe, list) else ([probe] if probe else [])
                dims = req.get("dimensions") or []
                db.add(CandidateEvidenceRequirement(
                    session_id=sid,
                    competency=req.get("competency") or "unknown",
                    dimension=req.get("dimension") or (dims[0] if dims else "technical"),
                    required_probes=probes or [],
                    evidence_level=req.get("evidence_level") or "behavioral",
                    snapshot=req,
                ))
        saved["evidence_requirements"] = existing["evidence_requirements"] or bool(requirements)

        await db.commit()
    except Exception as e:  # noqa: BLE001 - best-effort by design
        logger.warning(f"V5 intelligence persistence failed (best-effort): {e}")
        try:
            await db.rollback()
        except Exception:  # noqa: BLE001
            pass
    finally:
        if owns_session and db is not None:
            try:
                await db.close()
            except Exception:  # noqa: BLE001
                pass
    return saved


async def _has_row(db, model, session_id: UUID) -> bool:
    """True when the session already has a row for this artifact."""
    result = await db.execute(
        select(model.id).where(model.session_id == session_id).limit(1)
    )
    return result.scalar_one_or_none() is not None
