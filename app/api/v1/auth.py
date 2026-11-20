from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.google import verify_google_token
from app.auth.middleware import authenticate
from app.auth.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    MeResponse,
    OrgMembershipResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.accounts import finish_password_reset, find_user_by_email, is_org_account, start_password_reset
from app.auth.service import login, logout, refresh, register
from app.config import settings
from app.database.deps import get_db
from app.models.db import Organization, User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register_endpoint(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register(req, db)


@router.post("/login", response_model=AuthResponse)
async def login_endpoint(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await login(req, db)


@router.post("/google")
async def google_login_endpoint(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    from app.auth.service import google_login
    google_data = await verify_google_token(req.credential)
    return await google_login(google_data, db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await refresh(req.refresh_token, db)


@router.post("/logout", status_code=204)
async def logout_endpoint(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await logout(req.refresh_token, db)


@router.get("/me", response_model=MeResponse)
async def me_endpoint(user: User = Depends(authenticate), db: AsyncSession = Depends(get_db)):
    memberships = []
    result = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    for org in result.scalars().all():
        memberships.append(OrgMembershipResponse(
            org_id=org.id,
            org_name=org.name,
            org_slug=org.slug,
            role="owner",
        ))
    return MeResponse(
        user=UserResponse.model_validate(user),
        memberships=memberships,
    )


@router.post("/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    generic = {"message": "If that email exists, a reset link has been sent."}
    user = await find_user_by_email(db, req.email)
    # Only an account that can sign in on the hiring side gets a hiring reset link; guests and candidate-only accounts
    # use the candidate flow. The answer is the same either way, so it reveals nothing.
    if user is None or not user.is_active or not user.is_registered or not await is_org_account(db, user):
        return generic

    token = await start_password_reset(db, user)

    from app.services.email import send_email
    reset_url = f"{settings.APP_URL}/reset-password?token={token}"
    await send_email(
        to=user.email,
        subject="Reset your password — AI Interview Agent",
        template_name="password_reset.html",
        RESET_URL=reset_url,
        APP_URL=settings.APP_URL,
    )

    return generic


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    # Sets the new password and signs the account out everywhere (every kind of session).
    await finish_password_reset(db, req.token, req.new_password)
    return {"message": "Password reset successfully"}
