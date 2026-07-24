from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.auth.schemas import (
    AuthResponse,
    LoginRequest,
    OrgMembershipResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.database.deps import get_db
from app.models.db import Organization, OrgUser, RefreshToken, User


async def register(req: RegisterRequest, db: AsyncSession) -> AuthResponse:
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name,
    )
    db.add(user)
    await db.flush()

    slug = req.org_name.lower().replace(" ", "-") + "-" + uuid.uuid4().hex[:6]
    org = Organization(id=uuid.uuid4(), name=req.org_name, slug=slug)
    db.add(org)
    await db.flush()

    company = _create_default_company(org)
    db.add(company)
    await db.flush()

    membership = OrgUser(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)

    return await _build_auth_response(user, org, db)


async def login(req: LoginRequest, db: AsyncSession) -> AuthResponse:
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    org_result = await db.execute(
        select(OrgUser).where(OrgUser.user_id == user.id)
    )
    membership = org_result.scalar_one_or_none()
    org = None
    if membership:
        org_result = await db.execute(select(Organization).where(Organization.id == membership.org_id))
        org = org_result.scalar_one_or_none()

    return await _build_auth_response(user, org, db)


async def google_login(google_data: dict, db: AsyncSession) -> AuthResponse:
    email = google_data.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Google")

    name = google_data.get("name", email.split("@")[0])

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(uuid.uuid4().hex),
            name=name,
            avatar_url=google_data.get("avatar"),
        )
        db.add(user)
        await db.flush()

        slug = name.lower().replace(" ", "-") + "-" + uuid.uuid4().hex[:6]
        org = Organization(id=uuid.uuid4(), name=f"{name}'s Org", slug=slug)
        db.add(org)
        await db.flush()

        company = _create_default_company(org)
        db.add(company)
        await db.flush()

        membership = OrgUser(
            id=uuid.uuid4(),
            org_id=org.id,
            user_id=user.id,
            role="owner",
        )
        db.add(membership)
    else:
        result = await db.execute(
            select(OrgUser).where(OrgUser.user_id == user.id)
        )
        membership = result.scalar_one_or_none()

    org = None
    if membership:
        org_result = await db.execute(select(Organization).where(Organization.id == membership.org_id))
        org = org_result.scalar_one_or_none()

    return await _build_auth_response(user, org, db)


async def refresh(refresh_token: str, db: AsyncSession) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    token_id = payload.get("jti")
    user_id = payload.get("sub")
    if not token_id or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    stored = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == _hash(token_id))
    )
    stored_token = stored.scalar_one_or_none()
    if not stored_token or stored_token.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or not found")

    stored_token.revoked = True

    new_token_id = uuid.uuid4().hex
    new_refresh = RefreshToken(
        id=uuid.uuid4(),
        user_id=UUID(user_id),
        token_hash=_hash(new_token_id),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(new_refresh)

    access_token = create_access_token(user_id)
    refresh_token_str = create_refresh_token(user_id, new_token_id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
    )


async def logout(refresh_token: str, db: AsyncSession) -> None:
    try:
        payload = decode_token(refresh_token)
    except ValueError:
        return
    token_id = payload.get("jti")
    if token_id:
        stored = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == _hash(token_id))
        )
        stored_token = stored.scalar_one_or_none()
        if stored_token:
            stored_token.revoked = True
            await db.flush()


def _create_default_company(org: Organization):
    from app.models.db import Department
    return Department(
        org_id=org.id,
        name=f"{org.name} - Main",
        description="Default department",
    )


async def _build_auth_response(user: User, org: Optional[Organization], db: AsyncSession) -> AuthResponse:
    access_token = create_access_token(str(user.id), org_id=str(org.id) if org else None)
    token_id = uuid.uuid4().hex
    refresh_token_str = create_refresh_token(str(user.id), token_id)

    rt = RefreshToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=_hash(token_id),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(rt)
    await db.commit()
    await db.refresh(user)

    memberships = []
    if org:
        memberships.append(OrgMembershipResponse(
            org_id=org.id,
            org_name=org.name,
            org_slug=org.slug,
            role="owner",
        ))

    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_str,
        ),
        memberships=memberships,
    )


def _hash(token_id: str) -> str:
    return hashlib.sha256(token_id.encode()).hexdigest()
