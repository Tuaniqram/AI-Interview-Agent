from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import authenticate
from app.auth.rbac import require_org_role_path
from app.database.deps import get_db
from app.intelligence.role_competency_profiler import detect_family
from app.models.db import (
    CandidateProfile,
    ItRole,
    InterviewBrain,
    InterviewSession,
    Organization,
    ScorecardResult,
    User,
)

router = APIRouter(prefix="/orgs/{org_id}/candidates", tags=["candidate-ranking"])


def _score_band(score) -> str | None:
    """Coarse calibrated band (0-10 scale) for the ranking UI."""
    if score is None:
        return None
    if score >= 8.5:
        return "strong_hire"
    if score >= 7.5:
        return "hire"
    if score >= 6.5:
        return "lean_hire"
    return "concern"


def _calibration_fields(brain_metadata) -> dict:
    cal: dict = {}
    diff: dict = {}
    if isinstance(brain_metadata, dict):
        cal = brain_metadata.get("calibration_state") or {}
        diff = brain_metadata.get("difficulty_state") or {}
    return {
        "calibrated_score": cal.get("calibrated_score"),
        "difficulty_reached": cal.get(
            "difficulty_reached", diff.get("difficulty_reached")
        ),
        "role_floor": cal.get("role_floor", diff.get("role_floor")),
    }


def build_ranking_row(
    session, candidate, department, weighted_score, calibration_fields
) -> dict:
    """Compose one ranking entry from DB rows + a calibration snapshot.

    Pure — unit-testable without a database. ``session`` exposes ``id``,
    ``job_role``, ``final_score``, ``started_at``, ``ended_at``; candidate /
    department expose their display fields.
    """
    family = detect_family(str(session.job_role_snapshot or ""))
    calibrated_score = calibration_fields.get("calibrated_score")
    return {
        "session_id": str(session.id),
        "candidate_id": str(candidate.id) if candidate else None,
        "candidate_name": candidate.name if candidate else "Unknown",
        "candidate_email": candidate.email if candidate else None,
        "resume_url": candidate.resume_url if candidate else None,
        "skills": candidate.skills if candidate else None,
        "job_role": session.job_role_snapshot,
        "department_name": department.name if department else None,
        "department_id": department.id if department else None,
        "final_score": float(session.final_score) if session.final_score else None,
        "weighted_score": weighted_score,
        "calibrated_score": (
            float(calibrated_score) if calibrated_score is not None else None
        ),
        "difficulty_reached": calibration_fields.get("difficulty_reached"),
        "role_floor": calibration_fields.get("role_floor"),
        "family": family,
        "score_band": _score_band(calibrated_score),
        "comparable_note": None,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }


def annotate_comparability(rows: list[dict]) -> list[dict]:
    """Add ``comparable_note`` against the cohort's dominant family + floor.

    Calibrated scores are only directly comparable within a family cohort; a
    candidate whose family (or seniority floor) differs gets an explicit note.
    """
    if not rows:
        return rows
    counts: dict[str, int] = {}
    for row in rows:
        fam = row.get("family") or "technical"
        counts[fam] = counts.get(fam, 0) + 1
    cohort_family = max(counts, key=counts.get)
    for row in rows:
        note = None
        if row.get("family") != cohort_family:
            note = (
                f"Different family cohort ({row.get('family')}) — calibrated "
                f"score is not directly comparable to {cohort_family} candidates"
            )
        row["comparable_note"] = note
    return rows


def sort_rankings(rows: list[dict], sort_by: str = "final") -> list[dict]:
    """Sort a copy; ``calibrated`` ranks by calibrated score (nulls last)."""
    field = "calibrated_score" if sort_by == "calibrated" else "final_score"

    def _key(row: dict):
        score = row.get(field)
        return (score is None, -(score or 0))

    return sorted(rows, key=_key)


@router.get("/ranking")
async def get_candidate_ranking(
    org_id: UUID,
    department_id: int | None = Query(None),
    job_role: str | None = Query(None),
    family: str | None = Query(None, description="Filter to a detected job family (e.g. marketing)"),
    sort_by: str = Query("final", pattern="^(final|calibrated)$"),
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            InterviewSession,
            CandidateProfile,
            ItRole,
        )
        .join(CandidateProfile, InterviewSession.candidate_profile_id == CandidateProfile.id, isouter=True)
        .join(ItRole, InterviewSession.it_role_id == ItRole.id, isouter=True)
        .where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
            InterviewSession.status == "completed",
        )
        .order_by(desc(InterviewSession.final_score))
    )

    if job_role is not None:
        query = query.where(InterviewSession.job_role_snapshot.ilike(f"%{job_role}%"))

    result = await db.execute(query)
    rows = result.all()

    session_ids = [str(session.id) for session, _, _ in rows]
    scorecard_map = {}
    calibration_map = {}
    if session_ids:
        ids = [UUID(s) for s in session_ids]
        sc_result = await db.execute(
            select(ScorecardResult).where(
                ScorecardResult.session_id.in_(ids)
            )
        )
        for sr in sc_result.scalars().all():
            scorecard_map[str(sr.session_id)] = float(sr.weighted_score) if sr.weighted_score else None
        brain_result = await db.execute(
            select(InterviewBrain).where(
                InterviewBrain.session_id.in_(ids)
            )
        )
        for brain in brain_result.scalars().all():
            calibration_map[str(brain.session_id)] = _calibration_fields(brain.brain_metadata)

    rankings = []
    for session, candidate, department in rows:
        sid = str(session.id)
        rankings.append(
            build_ranking_row(
                session,
                candidate,
                department,
                scorecard_map.get(sid),
                calibration_map.get(sid, {}),
            )
        )

    if family is not None:
        rankings = [r for r in rankings if r.get("family") == family]

    rankings = annotate_comparability(rankings)
    rankings = sort_rankings(rankings, sort_by)
    for rank, entry in enumerate(rankings, 1):
        entry["rank"] = rank

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
            ItRole,
        )
        .join(CandidateProfile, InterviewSession.candidate_profile_id == CandidateProfile.id, isouter=True)
        .join(ItRole, InterviewSession.it_role_id == ItRole.id, isouter=True)
        .where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
            InterviewSession.status == "completed",
        )
        .order_by(desc(InterviewSession.final_score))
    )

    if job_role is not None:
        query = query.where(InterviewSession.job_role_snapshot.ilike(f"%{job_role}%"))

    result = await db.execute(query)
    rows = result.all()

    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Candidate Name", "Email", "Job Role", "ItRole", "Score", "Skills", "Date"])
    for session, candidate, department in rows:
        writer.writerow([
            candidate.name if candidate else "Unknown",
            candidate.email if candidate else "",
            session.job_role_snapshot,
            department.name if department else "",
            float(session.final_score) if session.final_score else "",
            candidate.skills if candidate and candidate.skills else "",
            session.ended_at.isoformat() if session.ended_at else "",
        ])

    return PlainTextResponse(output.getvalue(), media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=candidates_export.csv"
    })


@router.get("/ranking/summary")
async def get_ranking_summary(
    org_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            InterviewSession.job_role_snapshot,
            InterviewSession.it_role_id,
            ItRole.name.label("dept_name"),
            func.count(InterviewSession.id).label("total"),
            func.avg(InterviewSession.final_score).label("avg_score"),
            func.max(InterviewSession.final_score).label("max_score"),
            func.min(InterviewSession.final_score).label("min_score"),
        )
        .join(ItRole, InterviewSession.it_role_id == ItRole.id, isouter=True)
        .where(
            InterviewSession.org_id == org_id,
            InterviewSession.final_score.isnot(None),
            InterviewSession.status == "completed",
        )
        .group_by(InterviewSession.job_role_snapshot, InterviewSession.it_role_id, ItRole.name)
        .order_by(desc("avg_score"))
    )
    rows = result.all()
    return [
        {
            "job_role": row.job_role_snapshot,
            "department_id": row.it_role_id,
            "department_name": row.dept_name,
            "total_candidates": row.total,
            "average_score": round(float(row.avg_score), 2) if row.avg_score else None,
            "max_score": round(float(row.max_score), 2) if row.max_score else None,
            "min_score": round(float(row.min_score), 2) if row.min_score else None,
        }
        for row in rows
    ]
