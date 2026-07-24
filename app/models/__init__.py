"""
ORM models — import from here for type hints and Alembic autodetect.
"""
from app.models.db import (
    AuditLog,
    Booking,
    CandidateInvitation,
    CandidateProfile,
    CandidateSession,
    Department,
    DepartmentDocument,
    InterviewEvaluation,
    InterviewMessage,
    InterviewSession,
    InterviewSlot,
    InterviewTemplate,
    Organization,
    OrgUser,
    PublicInterview,
    PublicInterviewSubmission,
    RefreshToken,
    SlotAvailability,
    User,
)

__all__ = [
    "AuditLog", "Booking", "CandidateInvitation", "CandidateProfile", "CandidateSession",
    "Department", "DepartmentDocument", "InterviewEvaluation", "InterviewMessage",
    "InterviewSession", "InterviewSlot", "InterviewTemplate",
    "Organization", "OrgUser", "PublicInterview", "PublicInterviewSubmission",
    "RefreshToken", "SlotAvailability", "User",
]
