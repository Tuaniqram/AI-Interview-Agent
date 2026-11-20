from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.accounts import (
    ACTOR_ORG,
    clean_email,
    find_user_by_email,
    hash_token,
    is_org_account,
    issue_refresh_token,
    password_matches,
    rotate_refresh_token,
)
from app.auth.jwt import create_access_token, decode_token
from app.auth.password import hash_password
from app.auth.schemas import (
    AuthResponse,
    LoginRequest,
    OrgMembershipResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.models.db import Organization, RefreshToken, User

# Hiring-side sign-in only serves hiring accounts (an admin, or the owner of an organization). A candidate who has only a
# candidate account cannot use it to get a hiring session, and the error is the same as a wrong password.
_BAD_CREDENTIALS = "Invalid email or password"


async def register(req: RegisterRequest, db: AsyncSession) -> AuthResponse:
    if await find_user_by_email(db, req.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=clean_email(req.email),
        password_hash=hash_password(req.password),
        name=req.name,
        is_registered=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    slug = req.org_name.lower().replace(" ", "-") + "-" + uuid.uuid4().hex[:6]
    org = Organization(
        id=uuid.uuid4(),
        owner_user_id=user.id,
        name=req.org_name,
        slug=slug,
    )
    db.add(org)
    await db.flush()

    return await _build_auth_response(user, org, db)


async def login(req: LoginRequest, db: AsyncSession) -> AuthResponse:
    user = await find_user_by_email(db, req.email)
    if not password_matches(user, req.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    if not await is_org_account(db, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_BAD_CREDENTIALS)

    org_result = await db.execute(
        select(Organization).where(Organization.owner_user_id == user.id)
    )
    org = org_result.scalar_one_or_none()

    return await _build_auth_response(user, org, db)


async def google_login(google_data: dict, db: AsyncSession) -> AuthResponse:
    email = google_data.get("email")
    subject = google_data.get("sub")
    if not email or not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email not provided by Google")
    # verify_google_token already rejects unverified emails; this keeps the rule even if the service is called directly.
    if google_data.get("email_verified") is not True:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your Google email address is not verified")

    name = google_data.get("name") or email.split("@")[0]

    user = await find_user_by_email(db, email)

    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=clean_email(email),
            password_hash=None,
            name=name,
            avatar_url=google_data.get("avatar"),
            google_id=subject,
            is_registered=True,
            is_verified=True,
            verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()

        slug = name.lower().replace(" ", "-") + "-" + uuid.uuid4().hex[:6]
        org = Organization(
            id=uuid.uuid4(),
            owner_user_id=user.id,
            name=f"{name}'s Org",
            slug=slug,
        )
        db.add(org)
        await db.flush()
    else:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
        # An existing account is only signed in here if it is a hiring account, and only by the Google identity it is bound to.
        if not await is_org_account(db, user) or (user.google_id and user.google_id != subject):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This Google account cannot sign in here")
        if not user.google_id:
            user.google_id = subject
        result = await db.execute(
            select(Organization).where(Organization.owner_user_id == user.id)
        )
        org = result.scalar_one_or_none()

    return await _build_auth_response(user, org, db)


async def refresh(refresh_token: str, db: AsyncSession) -> TokenResponse:
    user, refresh_token_str = await rotate_refresh_token(db, refresh_token, ACTOR_ORG, allow=is_org_account)
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
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
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(token_id))
        )
        stored_token = stored.scalar_one_or_none()
        if stored_token:
            stored_token.revoked = True
            await db.flush()


async def _build_auth_response(user: User, org: Optional[Organization], db: AsyncSession) -> AuthResponse:
    access_token = create_access_token(str(user.id), org_id=str(org.id) if org else None)
    refresh_token_str = issue_refresh_token(db, user.id, ACTOR_ORG)
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


_hash = hash_token  # kept for callers that imported it from here
