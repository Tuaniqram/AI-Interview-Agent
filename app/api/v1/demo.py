"""Demo maintenance endpoints - local demo only.

Used by the end-to-end demo page to reset the lean interview runtime data
(interviews, evidence, hypotheses, brains) while keeping users, organizations,
organization documents, resumes, templates, marketplace listings, and the IT catalog.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])

WIPE_TABLES = [
    "interview_sessions",
]

KEPT_TABLES = [
    "users",
    "organizations",
    "refresh_tokens",
    "user_password_reset_tokens",
    "organization_documents",
    "it_roles",
    "competencies",
    "role_competencies",
    "candidate_profiles",
    "candidate_refresh_tokens",
    "candidate_password_reset_tokens",
    "candidate_documents",
    "candidate_invitations",
    "public_interviews",
    "public_interview_submissions",
    "candidate_saved_listings",
    "scorecard_templates",
    "interview_templates",
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
