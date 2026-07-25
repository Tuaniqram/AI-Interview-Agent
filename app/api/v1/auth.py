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
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.auth.password import hash_password
from app.auth.service import login, logout, refresh, register
from app.config import settings
from app.database.deps import get_db
from app.models.db import Organization, OrgUser, User, UserPasswordResetToken

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
        select(OrgUser, Organization)
        .join(Organization, OrgUser.org_id == Organization.id)
        .where(OrgUser.user_id == user.id)
    )
    for mu, org in result.all():
        memberships.append(OrgMembershipResponse(
            org_id=org.id,
            org_name=org.name,
            org_slug=org.slug,
            role=mu.role,
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
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user:
        return {"message": "If that email exists, a reset link has been sent."}

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset = UserPasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(reset)
    await db.commit()

    from app.services.email import send_email
    reset_url = f"{settings.APP_URL}/reset-password?token={token}"
    await send_email(
        to=user.email,
        subject="Reset your password — AI Interview Agent",
        template_name="password_reset.html",
        RESET_URL=reset_url,
        APP_URL=settings.APP_URL,
    )

    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hashlib.sha256(req.token.encode()).hexdigest()
    result = await db.execute(
        select(UserPasswordResetToken).where(
            UserPasswordResetToken.token_hash == token_hash,
            UserPasswordResetToken.used == False,
            UserPasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    reset = result.scalar_one_or_none()
    if not reset:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = hash_password(req.new_password)
    reset.used = True
    await db.commit()

    return {"message": "Password reset successfully"}
