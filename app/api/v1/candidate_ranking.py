from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_org_role_path
from app.database.deps import get_db
from app.models.db import (
    CandidateProfile,
    Department,
    InterviewSession,
    Organization,
    User,
)

router = APIRouter(prefix="/orgs/{org_id}/candidates", tags=["candidate-ranking"])


@router.get("/ranking")
async def get_candidate_ranking(
    org_id: UUID,
    department_id: int | None = Query(None),
    job_role: str | None = Query(None),
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            InterviewSession,
            CandidateProfile,
            Department,
        )
        .join(CandidateProfile, InterviewSession.candidate_profile_id == CandidateProfile.id, isouter=True)
        .join(Department, InterviewSession.department_id == Department.id, isouter=True)
        .where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
            InterviewSession.status == "completed",
        )
        .order_by(desc(InterviewSession.final_score))
    )

    if department_id is not None:
        query = query.where(InterviewSession.department_id == department_id)
    if job_role is not None:
        query = query.where(InterviewSession.job_role.ilike(f"%{job_role}%"))

    result = await db.execute(query)
    rows = result.all()

    rankings = []
    for rank, (session, candidate, department) in enumerate(rows, 1):
        rankings.append({
            "rank": rank,
            "session_id": str(session.id),
            "candidate_id": str(candidate.id) if candidate else None,
            "candidate_name": candidate.name if candidate else "Unknown",
            "candidate_email": candidate.email if candidate else None,
            "skills": candidate.skills if candidate else None,
            "job_role": session.job_role,
            "department_name": department.name if department else None,
            "department_id": department.id if department else None,
            "final_score": float(session.final_score) if session.final_score else None,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        })

    return rankings


@router.get("/export")
async def export_candidates_csv(
    org_id: UUID,
    department_id: int | None = Query(None),
    job_role: str | None = Query(None),
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    from fastapi.responses import PlainTextResponse

    query = (
        select(
            InterviewSession,
            CandidateProfile,
            Department,
        )
        .join(CandidateProfile, InterviewSession.candidate_profile_id == CandidateProfile.id, isouter=True)
        .join(Department, InterviewSession.department_id == Department.id, isouter=True)
        .where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
            InterviewSession.status == "completed",
        )
        .order_by(desc(InterviewSession.final_score))
    )

    if department_id is not None:
        query = query.where(InterviewSession.department_id == department_id)
    if job_role is not None:
        query = query.where(InterviewSession.job_role.ilike(f"%{job_role}%"))

    result = await db.execute(query)
    rows = result.all()

    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Candidate Name", "Email", "Job Role", "Department", "Score", "Skills", "Date"])
    for session, candidate, department in rows:
        writer.writerow([
            candidate.name if candidate else "Unknown",
            candidate.email if candidate else "",
            session.job_role,
            department.name if department else "",
            float(session.final_score) if session.final_score else "",
            candidate.skills if candidate and candidate.skills else "",
            session.ended_at.isoformat() if session.ended_at else "",
        ])

    return PlainTextResponse(output.getvalue(), media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=candidates_export.csv"
    })
async def get_ranking_summary(
    org_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            InterviewSession.job_role,
            InterviewSession.department_id,
            Department.name.label("dept_name"),
            func.count(InterviewSession.id).label("total"),
            func.avg(InterviewSession.final_score).label("avg_score"),
            func.max(InterviewSession.final_score).label("max_score"),
            func.min(InterviewSession.final_score).label("min_score"),
        )
        .join(Department, InterviewSession.department_id == Department.id, isouter=True)
        .where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
            InterviewSession.status == "completed",
        )
        .group_by(InterviewSession.job_role, InterviewSession.department_id, Department.name)
        .order_by(desc("avg_score"))
    )
    rows = result.all()
    return [
        {
            "job_role": row.job_role,
            "department_id": row.department_id,
            "department_name": row.dept_name,
            "total_candidates": row.total,
            "average_score": round(float(row.avg_score), 2) if row.avg_score else None,
            "max_score": round(float(row.max_score), 2) if row.max_score else None,
            "min_score": round(float(row.min_score), 2) if row.min_score else None,
        }
        for row in rows
    ]
