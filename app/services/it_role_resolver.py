from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.it_catalog import get_it_roles
from app.models.db import ItRole

_FALLBACK_SLUG = "software-engineer"


def match_it_role_slug(role: str) -> str:
    value = (role or "").strip().lower()
    if not value:
        return _FALLBACK_SLUG

    normalized = value.replace("_", "-")
    for item in get_it_roles():
        if normalized == item["slug"]:
            return item["slug"]
    for item in get_it_roles():
        if value == item["name"].strip().lower():
            return item["slug"]
    for item in get_it_roles():
        if normalized in item["slug"] or value in item["name"].strip().lower():
            return item["slug"]
    return _FALLBACK_SLUG


async def resolve_it_role(db: AsyncSession, role: str) -> ItRole:
    slug = match_it_role_slug(role)
    result = await db.execute(select(ItRole).where(ItRole.slug == slug))
    row = result.scalar_one_or_none()
    if row is not None:
        return row

    result = await db.execute(
        select(ItRole)
        .where(ItRole.is_active.is_(True))
        .order_by(ItRole.slug)
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise LookupError("IT role catalog is empty; seed it_roles first")
    return row


async def resolve_it_role_id(db: AsyncSession, role: str) -> UUID:
    return (await resolve_it_role(db, role)).id
