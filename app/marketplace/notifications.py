"""Application emails (received / invitation / outcome).

Every sender is a background-task entry point: it opens its own DB session,
never raises, and never affects the application state. When ``RESEND_API_KEY``
is not configured ``send_email`` logs "[EMAIL DISABLED]" and returns False.
"""
from __future__ import annotations

import html
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select

from app.config import settings
from app.models.db import (
    InterviewSession,
    Organization,
    PublicInterview,
    PublicInterviewSubmission,
)

logger = logging.getLogger(__name__)


def invite_url(token: str) -> str:
    return f"{settings.APP_URL.rstrip('/')}/application-invite/{token}"


def _e(value) -> str:
    """Template values come from user input (names, titles): escape for HTML."""
    return html.escape(str(value or ""), quote=True)


def _format_date(value: Optional[datetime]) -> str:
    return value.strftime("%d %b %Y") if value else "soon"


async def _load(application_id: str) -> Optional[dict]:
    from app.database.session import get_session_factory

    factory = get_session_factory()
    if factory is None:
        return None
    async with factory() as db:
        row = (
            await db.execute(
                select(PublicInterviewSubmission, PublicInterview, Organization.name)
                .join(PublicInterview, PublicInterviewSubmission.public_id == PublicInterview.id)
                .join(Organization, PublicInterview.org_id == Organization.id)
                .where(PublicInterviewSubmission.id == UUID(str(application_id)))
            )
        ).one_or_none()
        if row is None:
            return None
        submission, pi, org_name = row
        session = None
        if submission.session_id:
            session = (
                await db.execute(select(InterviewSession).where(InterviewSession.id == submission.session_id))
            ).scalar_one_or_none()
        return {
            "email": submission.candidate_email,
            "name": submission.candidate_name,
            "job_role": pi.title,
            "org_name": org_name,
            "outcome": submission.outcome,
            "invite_token": session.invite_token if session else None,
            "invite_expires_at": session.invite_expires_at if session else None,
        }


async def _send(application_id: str, kind: str, subject, template: str, variables) -> bool:
    from app.services.email import send_email

    try:
        data = await _load(application_id)
        if data is None:
            logger.warning("%s email skipped: application %s not found", kind, application_id)
            return False
        built = variables(data)
        if built is None:
            logger.warning("%s email skipped for %s: nothing to send", kind, application_id)
            return False
        sent = await send_email(
            to=data["email"],
            subject=subject(data),
            template_name=template,
            APP_URL=settings.APP_URL.rstrip("/"),
            **built,
        )
        if not sent:
            logger.warning("%s email for application %s was not sent", kind, application_id)
        return sent
    except Exception:  # noqa: BLE001 - email problems must never affect the application flow
        logger.exception("%s email failed for application %s", kind, application_id)
        return False


async def send_application_received_email(application_id: str) -> bool:
    return await _send(
        application_id,
        "application_received",
        lambda d: f"We received your application — {d['job_role']}",
        "application_received.html",
        lambda d: {
            "CANDIDATE_NAME": _e(d["name"]),
            "ORG_NAME": _e(d["org_name"]),
            "JOB_ROLE": _e(d["job_role"]),
            "REGISTER_URL": f"{settings.APP_URL.rstrip('/')}/candidate/register",
        },
    )


async def send_application_invitation_email(application_id: str) -> bool:
    return await _send(
        application_id,
        "application_invitation",
        lambda d: f"You're invited to interview — {d['job_role']} at {d['org_name']}",
        "application_invitation.html",
        lambda d: (
            {
                "CANDIDATE_NAME": _e(d["name"]),
                "ORG_NAME": _e(d["org_name"]),
                "JOB_ROLE": _e(d["job_role"]),
                "INVITE_URL": invite_url(d["invite_token"]),
                "EXPIRES_AT": _format_date(d["invite_expires_at"]),
            }
            if d["invite_token"]
            else None
        ),
    )


async def send_application_outcome_email(application_id: str) -> bool:
    messages = {
        "hired": ("Good news", "the team has decided to move forward with you"),
        "rejected": ("Application update", "thank you for your time; the team has decided not to move forward"),
    }

    def variables(d):
        if d["outcome"] not in messages:
            return None
        headline, message = messages[d["outcome"]]
        return {
            "HEADLINE": headline,
            "MESSAGE": message,
            "CANDIDATE_NAME": _e(d["name"]),
            "ORG_NAME": _e(d["org_name"]),
            "JOB_ROLE": _e(d["job_role"]),
        }

    return await _send(
        application_id,
        "application_outcome",
        lambda d: f"Update on your application — {d['job_role']}",
        "application_outcome.html",
        variables,
    )
