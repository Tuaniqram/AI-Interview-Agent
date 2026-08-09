"""Calibration loop (T4) — record post-hire outcomes and report drift.

``PUT /feedback/{session_id}`` snapshots the session's predicted verdict/score
(from the persisted ``interview_brain``) alongside the recruiter's actual
outcome. ``GET /drift`` and ``GET /drift/summary`` reconcile predicted vs
actual deterministically (see ``app/services/calibration_service.py``).
"""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_org_role_path
from app.database.deps import get_db
from app.intelligence.role_competency_profiler import detect_family
from app.models.db import (
    CalibrationFeedback,
    InterviewBrain,
    InterviewSession,
    User,
)
from app.services.calibration_service import (
    ACTUAL_OUTCOMES,
    build_drift_report,
    build_drift_summary,
)

router = APIRouter(prefix="/orgs/{org_id}/calibration", tags=["calibration"])


class FeedbackIn(BaseModel):
    actual_outcome: Literal[
        "strong_performance",
        "met_expectations",
        "below_expectations",
        "terminated_during_probation",
        "no_feedback",
    ]
    notes: str | None = None


def _predictions_for(brain) -> tuple[dict, dict]:
    cal: dict = {}
    diff: dict = {}
    if brain is not None:
        meta = brain.brain_metadata or {}
        cal = meta.get("calibration_state") or {}
        diff = meta.get("difficulty_state") or {}
    return cal, diff


@router.put("/feedback/{session_id}", status_code=status.HTTP_200_OK)
async def record_feedback(
    org_id: UUID,
    session_id: UUID,
    payload: FeedbackIn,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    session = (
        await db.execute(
            select(InterviewSession).where(
                InterviewSession.id == session_id,
                InterviewSession.org_id == org_id,
            )
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found in this organization",
        )
    if session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed sessions can receive outcome feedback",
        )

    brain = (
        await db.execute(
            select(InterviewBrain).where(InterviewBrain.session_id == session_id)
        )
    ).scalar_one_or_none()
    cal, diff = _predictions_for(brain)

    existing = (
        await db.execute(
            select(CalibrationFeedback).where(
                CalibrationFeedback.session_id == session_id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = CalibrationFeedback(session_id=session_id)
        db.add(existing)

    existing.org_id = org_id
    existing.department_id = session.department_id
    existing.job_role = session.job_role
    existing.predicted_verdict = cal.get("calibrated_verdict")
    existing.predicted_score = cal.get("calibrated_score")
    existing.difficulty_reached = cal.get(
        "difficulty_reached", diff.get("difficulty_reached")
    )
    existing.role_floor = cal.get("role_floor", diff.get("role_floor"))
    existing.actual_outcome = payload.actual_outcome
    existing.notes = payload.notes
    await db.commit()

    return {
        "session_id": str(session_id),
        "predicted_verdict": existing.predicted_verdict,
        "predicted_score": (
            float(existing.predicted_score)
            if existing.predicted_score is not None
            else None
        ),
        "actual_outcome": existing.actual_outcome,
        "recorded": True,
    }


@router.get("/drift")
async def get_drift_report(
    org_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(CalibrationFeedback).where(CalibrationFeedback.org_id == org_id)
        )
    ).scalars().all()
    feedback = [
        {
            "job_role": row.job_role,
            "family": detect_family(row.job_role or ""),
            "predicted_verdict": row.predicted_verdict,
            "predicted_score": (
                float(row.predicted_score)
                if row.predicted_score is not None
                else None
            ),
            "difficulty_reached": row.difficulty_reached,
            "role_floor": row.role_floor,
            "actual_outcome": row.actual_outcome,
        }
        for row in rows
    ]
    return build_drift_report(feedback)


@router.get("/drift/summary")
async def get_drift_summary(
    org_id: UUID,
    _: User = Depends(require_org_role_path(["owner", "member"])),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(CalibrationFeedback).where(CalibrationFeedback.org_id == org_id)
        )
    ).scalars().all()
    feedback = [
        {
            "predicted_verdict": row.predicted_verdict,
            "actual_outcome": row.actual_outcome,
            "difficulty_reached": row.difficulty_reached,
            "role_floor": row.role_floor,
        }
        for row in rows
    ]
    return build_drift_summary(feedback)
