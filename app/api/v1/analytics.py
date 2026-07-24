import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
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

    sessions_result = await db.execute(
        select(InterviewSession).where(InterviewSession.org_id == org_id)
    )
    rows = sessions_result.scalars().all()

    total = len(rows)
    active = len([r for r in rows if r.status in ("active", "in_progress")])
    completed = len([r for r in rows if r.status == "completed"])
    scores = [float(r.final_score) for r in rows if r.final_score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else None
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
        select(InterviewSession)
        .where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
        )
        .order_by(InterviewSession.started_at)
    )
    rows = result.scalars().all()

    daily: dict[str, list[float]] = {}
    for r in rows:
        if r.started_at:
            date_str = r.started_at.strftime("%Y-%m-%d")
            if date_str not in daily:
                daily[date_str] = []
            daily[date_str].append(float(r.final_score))

    return [
        ScoreTrendPoint(date=d, avg_score=round(sum(s) / len(s), 2), count=len(s))
        for d, s in sorted(daily.items())
    ]


@router.get("/scores/distribution", response_model=list[DistributionBucket])
async def scores_distribution(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        return []

    result = await db.execute(
        select(InterviewSession.final_score).where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
        )
    )
    scores = [float(row[0]) for row in result.all()]

    buckets = [
        {"range": "0-2", "min": 0, "max": 2, "count": 0},
        {"range": "3-4", "min": 3, "max": 4, "count": 0},
        {"range": "5-6", "min": 5, "max": 6, "count": 0},
        {"range": "7-8", "min": 7, "max": 8, "count": 0},
        {"range": "9-10", "min": 9, "max": 10, "count": 0},
    ]

    for s in scores:
        for b in buckets:
            if b["min"] <= s <= b["max"]:
                b["count"] += 1
                break

    return [DistributionBucket(range=b["range"], count=b["count"]) for b in buckets]


@router.get("/sessions/by-department", response_model=list[DepartmentSessionSummary])
async def sessions_by_department(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        return []

    departments_result = await db.execute(
        select(Department).where(Department.org_id == org_id)
    )
    departments = {d.id: d.name for d in departments_result.scalars().all()}

    sessions_result = await db.execute(
        select(InterviewSession).where(InterviewSession.org_id == org_id)
    )
    rows = sessions_result.scalars().all()

    grouped: dict[int, dict] = {}
    for r in rows:
        did = r.department_id
        if did not in grouped:
            grouped[did] = {"scores": [], "count": 0}
        grouped[did]["count"] += 1
        if r.final_score is not None:
            grouped[did]["scores"].append(float(r.final_score))

    result = []
    for did, data in grouped.items():
        scores = data["scores"]
        result.append(DepartmentSessionSummary(
            department_id=did,
            name=departments.get(did, f"Department {did}"),
            session_count=data["count"],
            avg_score=round(sum(scores) / len(scores), 2) if scores else None,
        ))

    result.sort(key=lambda x: x.session_count, reverse=True)
    return result


@router.get("/sessions/by-role", response_model=list[RoleSessionSummary])
async def sessions_by_role(
    org_id: str = Depends(_get_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    if not org_id:
        return []

    result = await db.execute(
        select(InterviewSession).where(InterviewSession.org_id == org_id)
    )
    rows = result.scalars().all()

    grouped: dict[str, dict] = {}
    for r in rows:
        role = r.job_role or "Unknown"
        if role not in grouped:
            grouped[role] = {"scores": [], "count": 0}
        grouped[role]["count"] += 1
        if r.final_score is not None:
            grouped[role]["scores"].append(float(r.final_score))

    result = []
    for role, data in grouped.items():
        scores = data["scores"]
        result.append(RoleSessionSummary(
            job_role=role,
            count=data["count"],
            avg_score=round(sum(scores) / len(scores), 2) if scores else None,
        ))

    result.sort(key=lambda x: x.count, reverse=True)
    return result
