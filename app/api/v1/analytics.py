import logging

from fastapi import APIRouter, Depends
from sqlalchemy import case, cast, Date, func, select, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_org_role, resolve_org_id
from app.database.deps import get_db
from app.models.db import Department, InterviewSession
from app.schemas.analytics import (
    DepartmentSessionSummary,
    DistributionBucket,
    OverviewResponse,
    RoleSessionSummary,
    ScoreTrendPoint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _get_org_id(org_id: str = Depends(resolve_org_id)) -> str:
    return org_id or ""


@router.get("/overview", response_model=OverviewResponse)
async def overview(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        return OverviewResponse()

    department_count = await db.scalar(
        select(func.count(Department.id)).where(Department.org_id == org_id)
    ) or 0

    row = await db.execute(
        select(
            func.count(InterviewSession.id).label("total"),
            func.count(case((InterviewSession.status.in_(["active", "in_progress"]), 1), else_=None)).label("active"),
            func.count(case((InterviewSession.status == "completed", 1), else_=None)).label("completed"),
            cast(func.avg(InterviewSession.final_score), Float).label("avg_score"),
        ).where(InterviewSession.org_id == org_id)
    )
    r = row.one()
    total = r.total or 0
    active = r.active or 0
    completed = r.completed or 0
    avg_score = round(r.avg_score, 2) if r.avg_score is not None else None
    completion_rate = round(completed / total * 100, 1) if total > 0 else 0

    return OverviewResponse(
        total_departments=department_count or 0,
        total_sessions=total,
        active_sessions=active,
        completed_sessions=completed,
        average_score=avg_score,
        completion_rate=completion_rate,
    )


@router.get("/scores/trend", response_model=list[ScoreTrendPoint])
async def scores_trend(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        return []

    result = await db.execute(
        select(
            cast(InterviewSession.started_at, Date).label("date"),
            cast(func.avg(InterviewSession.final_score), Float).label("avg_score"),
            func.count(InterviewSession.id).label("count"),
        )
        .where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
        )
        .group_by(cast(InterviewSession.started_at, Date))
        .order_by(cast(InterviewSession.started_at, Date))
    )
    return [
        ScoreTrendPoint(date=str(r.date), avg_score=round(r.avg_score, 2), count=r.count)
        for r in result.all()
    ]


@router.get("/scores/distribution", response_model=list[DistributionBucket])
async def scores_distribution(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        return []

    buckets = [
        ("0-2", 0, 2),
        ("3-4", 3, 4),
        ("5-6", 5, 6),
        ("7-8", 7, 8),
        ("9-10", 9, 10),
    ]
    result = []
    for label, lo, hi in buckets:
        count = await db.scalar(
            select(func.count(InterviewSession.id)).where(
                InterviewSession.org_id == org_id,
                InterviewSession.final_score.isnot(None),
                InterviewSession.final_score >= lo,
                InterviewSession.final_score <= hi,
            )
        ) or 0
        result.append(DistributionBucket(range=label, count=count))
    return result


@router.get("/sessions/by-department", response_model=list[DepartmentSessionSummary])
async def sessions_by_department(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        return []

    result = await db.execute(
        select(
            Department.id.label("department_id"),
            Department.name,
            func.count(InterviewSession.id).label("session_count"),
            cast(func.avg(InterviewSession.final_score), Float).label("avg_score"),
        )
        .outerjoin(InterviewSession, InterviewSession.department_id == Department.id)
        .where(Department.org_id == org_id)
        .group_by(Department.id, Department.name)
        .order_by(func.count(InterviewSession.id).desc())
    )
    return [
        DepartmentSessionSummary(
            department_id=r.department_id,
            name=r.name,
            session_count=r.session_count,
            avg_score=round(r.avg_score, 2) if r.avg_score is not None else None,
        )
        for r in result.all()
    ]


@router.get("/sessions/by-role", response_model=list[RoleSessionSummary])
async def sessions_by_role(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        return []

    result = await db.execute(
        select(
            func.coalesce(InterviewSession.job_role, "Unknown").label("job_role"),
            func.count(InterviewSession.id).label("count"),
            cast(func.avg(InterviewSession.final_score), Float).label("avg_score"),
        )
        .where(InterviewSession.org_id == org_id)
        .group_by(InterviewSession.job_role)
        .order_by(func.count(InterviewSession.id).desc())
    )
    return [
        RoleSessionSummary(
            job_role=r.job_role,
            count=r.count,
            avg_score=round(r.avg_score, 2) if r.avg_score is not None else None,
        )
        for r in result.all()
    ]
