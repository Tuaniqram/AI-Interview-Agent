import hashlib
import json
import secrets
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.candidates.auth import authenticate_candidate, require_verified_candidate
from app.candidates.schemas import (
    CandidateAuthResponse,
    CandidateClaimPendingResponse,
    CandidateClaimRequest,
    CandidateForgotPasswordRequest,
    CandidateInterviewResponse,
    CandidateLoginRequest,
    CandidateProfileResponse,
    CandidateRefreshRequest,
    CandidateRegisterRequest,
    CandidateResetPasswordRequest,
    CandidateTokenResponse,
    CandidateUpdateRequest,
    GoogleAuthRequest,
    PracticeStartRequest,
    PracticeStartResponse,
)
from app.services.audit_log import AuditLogService
from app.candidates.service import (
    complete_claim,
    get_competency_scores,
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
from app.candidates.resume_service import parse_resume, store_candidate_resume
from app.auth.rbac import require_org_role_path
from app.database.deps import get_db
from app.auth.middleware import authenticate
from app.models.db import (
    CandidatePasswordResetToken,
    CandidateProfile,
    CandidateRefreshToken,
    CandidateSavedListing,
    Organization,
    PublicInterview,
    PublicInterviewSubmission,
    User,
)
from app.auth.password import hash_password
from app.config import settings

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/register", response_model=CandidateAuthResponse | CandidateClaimPendingResponse)
async def register_endpoint(req: CandidateRegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await register(req, db)
    if isinstance(result, CandidateClaimPendingResponse):
        return result  # guest profile exists: finish via the emailed link (POST /claim)

    from app.services.email import send_email
    candidate_id = result.candidate.id
    profile_result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
    profile = profile_result.scalar_one_or_none()
    if profile and not profile.is_verified:
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        profile.verification_token_hash = token_hash
        profile.verification_sent_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
        await db.commit()
        verify_url = f"{settings.APP_URL}/candidate/verify?token={token}"
        await send_email(
            to=profile.email,
            subject="Verify your email — AI Interview Agent",
            template_name="verification.html",
            VERIFY_URL=verify_url,
            APP_URL=settings.APP_URL,
        )

    return result


@router.post("/claim", response_model=CandidateAuthResponse)
async def claim_endpoint(req: CandidateClaimRequest, db: AsyncSession = Depends(get_db)):
    """Finish claiming a guest profile: emailed token + a new password. Logs the candidate in."""
    return await complete_claim(req, db)


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

    from app.services.email import send_email
    verify_url = f"{settings.APP_URL}/candidate/verify?token={token}"
    await send_email(
        to=candidate.email,
        subject="Verify your email — AI Interview Agent",
        template_name="verification.html",
        VERIFY_URL=verify_url,
        APP_URL=settings.APP_URL,
    )

    return {"message": "Verification email sent"}


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
    if not candidate or not candidate.is_registered:
        # Tokens on unregistered guest profiles are claim tokens: they go through POST /claim.
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


@router.get("/competency-scores")
async def competency_scores_endpoint(
    candidate: CandidateProfile = Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    return await get_competency_scores(candidate.id, db)


@router.post("/saved-listings/{listing_id}")
async def save_listing(
    listing_id: int,
    candidate: CandidateProfile = Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(CandidateSavedListing).where(
            CandidateSavedListing.candidate_id == candidate.id,
            CandidateSavedListing.listing_id == listing_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Already saved"}
    saved = CandidateSavedListing(
        id=__import__('uuid').uuid4(),
        candidate_id=candidate.id,
        listing_id=listing_id,
    )
    db.add(saved)
    await db.commit()
    return {"message": "Listing saved"}


@router.delete("/saved-listings/{listing_id}")
async def unsave_listing(
    listing_id: int,
    candidate: CandidateProfile = Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CandidateSavedListing).where(
            CandidateSavedListing.candidate_id == candidate.id,
            CandidateSavedListing.listing_id == listing_id,
        )
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not saved")
    await db.delete(saved)
    await db.commit()
    return {"message": "Listing unsaved"}


@router.get("/saved-listings")
async def list_saved_listings(
    candidate: CandidateProfile = Depends(require_verified_candidate),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CandidateSavedListing, PublicInterview, Organization)
        .join(PublicInterview, CandidateSavedListing.listing_id == PublicInterview.id)
        .join(Organization, PublicInterview.org_id == Organization.id)
        .where(CandidateSavedListing.candidate_id == candidate.id)
        .order_by(CandidateSavedListing.created_at.desc())
    )
    listings = []
    for saved, pi, org in result.all():
        listings.append({
            "id": pi.id,
            "title": pi.title,
            "org_name": org.name,
            "org_slug": org.slug,
            "department_name": pi.department_name,
            "interview_mode": pi.interview_mode,
            "description": pi.description,
            "skills_required": pi.skills_required,
            "starts_at": pi.starts_at.isoformat() if pi.starts_at else None,
            "expires_at": pi.expires_at.isoformat() if pi.expires_at else None,
            "is_open": pi.is_open,
        })
    return listings


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
        req.interview_style,
        db,
    )


@router.post("/forgot-password")
async def forgot_password(
    req: CandidateForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    generic = {"message": "If that email exists, a reset link has been sent."}
    result = await db.execute(
        select(CandidateProfile).where(func.lower(CandidateProfile.email) == req.email.strip().lower())
    )
    candidate = result.scalars().first()
    # Guest profiles have no account yet: they claim it through registration, not a reset.
    if not candidate or not candidate.is_registered:
        return generic

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset = CandidatePasswordResetToken(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        token_hash=token_hash,
        expires_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc) + __import__('datetime').timedelta(hours=1),
    )
    db.add(reset)
    await db.commit()

    from app.services.email import send_email
    reset_url = f"{settings.APP_URL}/candidate/reset-password?token={token}"
    await send_email(
        to=candidate.email,
        subject="Reset your password — AI Interview Agent",
        template_name="password_reset.html",
        RESET_URL=reset_url,
        APP_URL=settings.APP_URL,
    )

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    req: CandidateResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    token, new_password = req.token, req.new_password
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(CandidatePasswordResetToken).where(
            CandidatePasswordResetToken.token_hash == token_hash,
            CandidatePasswordResetToken.used == False,
            CandidatePasswordResetToken.expires_at > __import__('datetime').datetime.now(__import__('datetime').timezone.utc),
        )
    )
    reset = result.scalar_one_or_none()
    if not reset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    candidate_result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == reset.candidate_id))
    candidate = candidate_result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    candidate.password_hash = hash_password(new_password)
    reset.used = True
    # Anyone holding an old session must sign in again with the new password.
    await db.execute(
        update(CandidateRefreshToken)
        .where(CandidateRefreshToken.candidate_id == candidate.id)
        .values(revoked=True)
    )
    await db.commit()

    return {"message": "Password reset successfully"}


@router.post("/me/resume", response_model=CandidateProfileResponse)
async def upload_resume(
    file: UploadFile = File(...),
    candidate: CandidateProfile = Depends(authenticate_candidate),
    db: AsyncSession = Depends(get_db),
):
    document = await store_candidate_resume(candidate, file, db)

    parsed = await parse_resume(document.extracted_text or "")
    profile_data = dict(candidate.profile_data or {})
    profile_data["resume_parsed"] = parsed
    candidate.profile_data = profile_data

    skills_list = parsed.get("skills", [])
    if skills_list:
        existing_skills = set(s.strip().lower() for s in (candidate.skills or "").split(",") if s.strip())
        existing_skills.update(s.lower() for s in skills_list)
        candidate.skills = ", ".join(sorted(existing_skills))

    document.document_metadata = {
        **(document.document_metadata or {}),
        "parsed_keys": list(parsed.keys()),
    }
    await db.commit()
    await db.refresh(candidate)

    response = CandidateProfileResponse.model_validate(candidate)
    response.resume_document_id = document.id
    return response


@router.get("/{candidate_id}/resume")
async def download_resume(
    candidate_id: UUID,
    org_id: UUID = Query(...),
    user: User = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_org_role_path(["owner", "member"])),
):
    # Only organizations that received an application from this candidate may read their CV.
    if not user.is_admin:
        received = await db.execute(
            select(PublicInterviewSubmission.id)
            .join(PublicInterview, PublicInterviewSubmission.public_id == PublicInterview.id)
            .where(
                PublicInterviewSubmission.candidate_profile_id == candidate_id,
                PublicInterview.org_id == org_id,
            )
            .limit(1)
        )
        if received.first() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    if not candidate or not candidate.resume_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    from fastapi.responses import Response

    from app.services import cv_storage

    content = await cv_storage.read(candidate.resume_url)
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume file not found")
    safe_name = candidate.name.replace(" ", "_").replace('"', "")
    filename = f"{safe_name}_resume.pdf"
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
