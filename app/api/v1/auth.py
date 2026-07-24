from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.google import verify_google_token
from app.auth.middleware import authenticate
from app.auth.schemas import (
    AuthResponse,
    GoogleAuthRequest,
    LoginRequest,
    MeResponse,
    OrgMembershipResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.service import login, logout, refresh, register
from app.database.deps import get_db
from app.models.db import Organization, OrgUser, User

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
