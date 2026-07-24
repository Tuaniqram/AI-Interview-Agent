import hashlib
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.auth import authenticate_candidate, require_verified_candidate
from app.candidates.schemas import (
    CandidateAuthResponse,
    CandidateInterviewResponse,
    CandidateLoginRequest,
    CandidateProfileResponse,
    CandidateRefreshRequest,
    CandidateRegisterRequest,
    CandidateTokenResponse,
    CandidateUpdateRequest,
    GoogleAuthRequest,
    PracticeStartRequest,
    PracticeStartResponse,
)
from app.services.audit_log import AuditLogService
from app.candidates.service import (
    get_interview_detail,
    get_interviews,
    get_profile,
    get_stats,
    login,
    refresh,
    register,
    start_practice,
    update_profile,
)
from app.database.deps import get_db
from app.models.db import CandidateProfile

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/register", response_model=CandidateAuthResponse)
async def register_endpoint(req: CandidateRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register(req, db)


@router.post("/login", response_model=CandidateAuthResponse)
async def login_endpoint(req: CandidateLoginRequest, db: AsyncSession = Depends(get_db)):
    return await login(req, db)


@router.post("/google")
async def google_login_endpoint(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    from app.auth.google import verify_google_token
    from app.candidates.service import google_login as candidate_google_login
    google_data = await verify_google_token(req.credential)
    return await candidate_google_login(google_data, db)


@router.post("/send-verification")
async def send_verification(
    candidate: CandidateProfile = Depends(authenticate_candidate),
    db: AsyncSession = Depends(get_db),
):
    if candidate.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already verified")
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    candidate.verification_token_hash = token_hash
    candidate.verification_sent_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    await db.commit()
    # TODO: send actual email — for now, log token to console
    print(f"[VERIFICATION] Token for {candidate.email}: {token}")
    return {"message": "Verification email sent", "token_preview": token[:8] + "..."}


@router.post("/verify")
async def verify_email(
    token: str = Query(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.verification_token_hash == token_hash)
    )
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")
    candidate.is_verified = True
    candidate.verified_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    candidate.verification_token_hash = None
    await db.commit()

    audit = AuditLogService(db)
    await audit.log(
        action="candidate.verify",
        resource_type="candidate_profile",
        resource_id=str(candidate.id),
        details={"email": candidate.email},
        ip_address=request.client.host if request and request.client else None,
    )

    return {"message": "Email verified successfully"}


@router.post("/refresh", response_model=CandidateTokenResponse)
async def refresh_endpoint(req: CandidateRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await refresh(req.refresh_token, db)


@router.get("/me", response_model=CandidateProfileResponse)
async def me_endpoint(
    candidate: CandidateProfile = Depends(authenticate_candidate),
):
    return CandidateProfileResponse.model_validate(candidate)


@router.patch("/me", response_model=CandidateProfileResponse)
async def update_me_endpoint(
    req: CandidateUpdateRequest,
    candidate: CandidateProfile = Depends(authenticate_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await update_profile(candidate.id, req, db)


@router.get("/interviews", response_model=list[CandidateInterviewResponse])
async def list_interviews_endpoint(
    candidate: CandidateProfile = Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await get_interviews(candidate.id, db)


@router.get("/interviews/{interview_id}")
async def interview_detail_endpoint(
    interview_id: UUID,
    candidate: CandidateProfile = Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await get_interview_detail(candidate.id, interview_id, db)


@router.get("/stats")
async def stats_endpoint(
    candidate: CandidateProfile = Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await get_stats(candidate.id, db)


@router.post("/practice/start", response_model=PracticeStartResponse)
async def start_practice_endpoint(
    req: PracticeStartRequest,
    candidate: CandidateProfile = Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await start_practice(
        candidate.id,
        req.job_role,
        req.difficulty,
        req.tech_stack,
        req.num_questions,
        db,
    )
