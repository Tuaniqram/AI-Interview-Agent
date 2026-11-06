"""Best-effort persistence for V5 intelligence artifacts.

All intelligence bundles now live in one ``interview_intelligence`` row per
session. Failures are swallowed; persistence must never break an interview.
"""
import logging
from uuid import UUID

from sqlalchemy import select

from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


async def persist_intelligence_bundle(
    session_id,
    org_id,
    job_role: str,
    bundle: dict,
    db=None,
) -> dict:
    """Upsert the consolidated intelligence row for a session.

    ``org_id`` is accepted for compatibility with the session-start path.
    Returns per-artifact saved flags for API callers.
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
        from app.models.db import InterviewIntelligence

        result = await db.execute(
            select(InterviewIntelligence).where(
                InterviewIntelligence.session_id == sid
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = InterviewIntelligence(session_id=sid)
            db.add(row)

        company_brain = bundle.get("company_brain") or {}
        candidate_brain = bundle.get("candidate_brain") or {}
        blueprint = bundle.get("interview_blueprint") or {}
        scorecard = bundle.get("scorecard") or {
            "competencies": blueprint.get("scorecard_competencies") or []
        }

        row.company_context = company_brain
        row.candidate_context = candidate_brain
        row.blueprint = blueprint
        row.scorecard = scorecard
        row.evidence_requirements = bundle.get("evidence_requirements") or []
        row.objectives = blueprint.get("objectives") or []
        row.consistency_checks = bundle.get("consistency_checks") or []
        row.observations = bundle.get("observations") or []
        row.evidence_graph = bundle.get("evidence_graph") or {}

        saved["company_brain"] = bool(company_brain)
        saved["scorecard"] = bool(scorecard)
        saved["blueprint"] = bool(blueprint)
        saved["candidate_brain"] = bool(candidate_brain)
        saved["evidence_requirements"] = bool(row.evidence_requirements)

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
