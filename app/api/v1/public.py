from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.marketplace.schemas import StartInterviewRequest, StartInterviewResponse
from app.marketplace.service import start_public_interview
from app.models.db import PublicInterview
from app.services.audit_log import AuditLogService

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/interviews/{token}/start", response_model=StartInterviewResponse)
async def start_interview_by_token(
    token: str,
    req: StartInterviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(PublicInterview).where(
            PublicInterview.token == token,
            PublicInterview.is_open == True,
            (PublicInterview.starts_at == None) | (PublicInterview.starts_at <= now),
            (PublicInterview.expires_at == None) | (PublicInterview.expires_at > now),
        )
    )
    pi = result.scalar_one_or_none()
    if not pi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found or expired")

    resp = await start_public_interview(str(pi.id), req, db)

    audit = AuditLogService(db)
    await audit.log(
        action="public_interview.start",
        resource_type="public_interview_submission",
        resource_id=str(pi.id),
        org_id=str(pi.org_id),
        details={"candidate_email": req.candidate_email, "candidate_name": req.candidate_name},
        ip_address=request.client.host if request.client else None,
    )

    return resp
