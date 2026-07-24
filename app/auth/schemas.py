from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    org_name: str = Field(default="My Organization")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    avatar_url: Optional[str] = None
    is_admin: bool
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrgMembershipResponse(BaseModel):
    org_id: UUID
    org_name: str
    org_slug: str
    role: str


class GoogleAuthRequest(BaseModel):
    credential: str


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse
    memberships: list[OrgMembershipResponse]


class MeResponse(BaseModel):
    user: UserResponse
    memberships: list[OrgMembershipResponse]
