"""Demo maintenance endpoints — local demo only.

Used by the end-to-end demo page to reset the interview/V5 runtime data
(interviews, evidence, hypotheses, brains, scorecards, marketplace listings,
bookings) while keeping the demo's org / department / documents / candidates /
templates intact.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])

# Wipe set — order matters for FK-safe deletes:
#   1. interview_sessions  -> DB-level CASCADE clears: interview_messages,
#      interview_evaluations, evidence_store, hypotheses, interview_objectives,
#      consistency_checks, observations, scorecards, scorecard_results,
#      company_brains, interview_blueprints, candidate_brains,
#      candidate_evidence_requirements, interview_brain, evidence_graph,
#      interview_timeline, candidate_sessions, public_interview_submissions,
#      candidate_documents
#   2. public_interviews   -> cascades: public_interview_submissions,
#      candidate_saved_listings
#   3. interview_slots     -> cascades: slot_availability, bookings
#   4. v4_session_state    -> raw-SQL checkpoint table, no ORM model, no dependents
WIPE_TABLES = [
    "interview_sessions",
    "public_interviews",
    "interview_slots",
    "v4_session_state",
]

KEPT_TABLES = [
    "users",
    "organizations",
    "org_users",
    "org_invitations",
    "departments",
    "department_documents",
    "candidate_profiles",
    "candidate_invitations",
    "candidate_refresh_tokens",
    "candidate_password_reset_tokens",
    "user_password_reset_tokens",
    "refresh_tokens",
    "interview_templates",
    "scorecard_templates",
    "audit_log",
]


@router.post("/refresh-db")
async def refresh_demo_db(db: AsyncSession = Depends(get_db)):
    """Wipe all interview/V5 runtime data and listings, keep demo data.

    Local demo tool — refused unless the app is served from localhost.
    """
    is_dev = "localhost" in settings.APP_URL or "127.0.0.1" in settings.APP_URL
    if not is_dev:
        raise HTTPException(
            status_code=403, detail="Demo refresh is local-dev only"
        )

    deleted: dict[str, int] = {}
    for table in WIPE_TABLES:
        result = await db.execute(text(f'DELETE FROM "{table}"'))
        deleted[table] = result.rowcount or 0
    await db.commit()

    logger.info("Demo DB refreshed — wiped %s", deleted)
    return {
        "message": (
            "Demo DB refreshed — interview/V5 runtime + listings wiped, "
            "org / departments / docs / candidates / templates kept"
        ),
        "deleted": deleted,
        "kept": KEPT_TABLES,
    }
