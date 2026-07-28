"""
ORM models — import from here for type hints and Alembic autodetect.
"""
from app.models.db import (
    AuditLog,
    Booking,
    CandidateInvitation,
    CandidateProfile,
    CandidateRefreshToken,
    CandidateSession,
    ConsistencyCheck,
    Department,
    DepartmentDocument,
    EvidenceStore,
    Hypothesis,
    InterviewEvaluation,
    InterviewMessage,
    InterviewObjective,
    InterviewSession,
    InterviewSlot,
    InterviewTemplate,
    Observation,
    Organization,
    OrgUser,
    PublicInterview,
    PublicInterviewSubmission,
    RefreshToken,
    ScorecardResult,
    ScorecardTemplate,
    SlotAvailability,
    User,
)

__all__ = [
    "AuditLog", "Booking", "CandidateInvitation", "CandidateProfile", "CandidateRefreshToken",
    "CandidateSession",
    "ConsistencyCheck", "Department", "DepartmentDocument", "EvidenceStore", "Hypothesis",
    "InterviewEvaluation", "InterviewMessage", "InterviewObjective", "InterviewSession",
    "InterviewSlot", "InterviewTemplate", "Observation", "Organization", "OrgUser",
    "PublicInterview", "PublicInterviewSubmission", "RefreshToken", "ScorecardResult",
    "ScorecardTemplate", "SlotAvailability", "User",
]
