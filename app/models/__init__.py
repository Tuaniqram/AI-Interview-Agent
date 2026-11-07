"""
ORM models — import from here for type hints and Alembic autodetect.
"""
from app.models.db import (
    AuditLog,
    CandidateDocument,
    CandidateInvitation,
    CandidateProfile,
    CandidateRefreshToken,
    Competency,
    EvidenceStore,
    Hypothesis,
    InterviewBrain,
    InterviewEvaluation,
    InterviewIntelligence,
    InterviewMessage,
    InterviewSession,
    InterviewTemplate,
    InterviewTimeline,
    ItRole,
    Organization,
    OrganizationDocument,
    PublicInterview,
    PublicInterviewSubmission,
    RefreshToken,
    RoleCompetency,
    ScorecardResult,
    ScorecardTemplate,
    User,
)

__all__ = [
    "AuditLog", "CandidateDocument",
    "CandidateInvitation", "CandidateProfile",
    "CandidateRefreshToken", "Competency",
    "EvidenceStore", "Hypothesis", "InterviewBrain",
    "InterviewEvaluation", "InterviewIntelligence", "InterviewMessage",
    "InterviewSession", "InterviewTemplate", "InterviewTimeline", "ItRole", "Organization", "OrganizationDocument", "PublicInterview",
    "PublicInterviewSubmission", "RefreshToken", "RoleCompetency", "ScorecardResult", "ScorecardTemplate", "User",
]
