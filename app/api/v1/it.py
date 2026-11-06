from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.database.deps import get_db
from app.models.db import Competency, ItRole, RoleCompetency, User

router = APIRouter(prefix="/it", tags=["it-catalog"])


@router.get("/roles")
async def list_it_roles(
    family: Optional[str] = Query(None),
    active_only: bool = Query(True),
    _: User = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    query = select(ItRole)
    if active_only:
        query = query.where(ItRole.is_active.is_(True))
    if family:
        query = query.where(ItRole.family == family)
    query = query.order_by(ItRole.family, ItRole.name)

    rows = (await db.execute(query)).scalars().all()
    return [
        {
            "id": str(role.id),
            "slug": role.slug,
            "family": role.family,
            "name": role.name,
            "description": role.description,
            "level_min": role.level_min,
            "level_max": role.level_max,
            "is_active": role.is_active,
        }
        for role in rows
    ]


@router.get("/roles/{slug}")
async def get_it_role(
    slug: str,
    _: User = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ItRole).where(ItRole.slug == slug))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IT role not found")
    return {
        "id": str(role.id),
        "slug": role.slug,
        "family": role.family,
        "name": role.name,
        "description": role.description,
        "level_min": role.level_min,
        "level_max": role.level_max,
        "is_active": role.is_active,
    }


@router.get("/roles/{slug}/competencies")
async def get_it_role_competencies(
    slug: str,
    _: User = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    role_result = await db.execute(select(ItRole).where(ItRole.slug == slug))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IT role not found")

    result = await db.execute(
        select(RoleCompetency, Competency)
        .join(Competency, RoleCompetency.competency_id == Competency.id)
        .where(RoleCompetency.role_id == role.id)
        .order_by(RoleCompetency.weight.desc(), Competency.name)
    )
    return [
        {
            "competency_id": comp.id,
            "name": comp.name,
            "category": comp.category,
            "primary_dimension": comp.primary_dimension,
            "weight": float(link.weight) if link.weight is not None else None,
            "required_level": link.required_level,
            "is_core": link.is_core,
        }
        for link, comp in result.all()
    ]


@router.get("/competencies")
async def list_competencies(
    category: Optional[str] = Query(None),
    _: User = Depends(authenticate),
    db: AsyncSession = Depends(get_db),
):
    query = select(Competency).where(Competency.is_active.is_(True))
    if category:
        query = query.where(Competency.category == category)
    query = query.order_by(Competency.category, Competency.name)
    rows = (await db.execute(query)).scalars().all()
    return [
        {
            "id": comp.id,
            "name": comp.name,
            "category": comp.category,
            "primary_dimension": comp.primary_dimension,
            "evidence_dimensions": comp.evidence_dimensions or [],
            "default_min_evidence": comp.default_min_evidence,
            "scope": comp.scope,
        }
        for comp in rows
    ]
