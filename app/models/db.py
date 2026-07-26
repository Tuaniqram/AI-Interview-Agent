from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey,
    Index, Integer, Numeric, Text, Time, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID, INET, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    org_memberships: Mapped[list[OrgUser]] = relationship(
        "OrgUser", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="OrgUser.user_id",
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    members: Mapped[list[OrgUser]] = relationship(
        "OrgUser", back_populates="organization", cascade="all, delete-orphan"
    )
    departments: Mapped[list[Department]] = relationship(
        "Department", back_populates="organization"
    )
    interview_slots: Mapped[list[InterviewSlot]] = relationship(
        "InterviewSlot", back_populates="organization", cascade="all, delete-orphan"
    )
    public_interviews: Mapped[list[PublicInterview]] = relationship(
        "PublicInterview", back_populates="organization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_orgs_slug", "slug"),
    )


class OrgUser(Base):
    __tablename__ = "org_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    invited_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    joined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped[Organization] = relationship("Organization", back_populates="members")
    user: Mapped[User] = relationship("User", back_populates="org_memberships", foreign_keys=[user_id])
    inviter: Mapped[Optional[User]] = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        CheckConstraint("role IN ('owner','member','viewer')", name="org_users_role_check"),
        Index("idx_org_users_org", "org_id"),
        Index("idx_org_users_user", "user_id"),
    )


class OrgInvitation(Base):
    __tablename__ = "org_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    inviter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default="member")
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped[Organization] = relationship("Organization")
    inviter: Mapped[User] = relationship("User", foreign_keys=[inviter_id])

    __table_args__ = (
        CheckConstraint("status IN ('pending','accepted','expired')",
                        name="org_invitations_status_check"),
        Index("idx_org_invitations_token", "token"),
        Index("idx_org_invitations_email", "email"),
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped[Optional[Organization]] = relationship("Organization", back_populates="departments")
    documents: Mapped[list[DepartmentDocument]] = relationship(
        "DepartmentDocument", back_populates="department", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[InterviewSession]] = relationship(
        "InterviewSession", back_populates="department"
    )
    templates: Mapped[list[InterviewTemplate]] = relationship(
        "InterviewTemplate", back_populates="department", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_departments_org", "org_id"),
    )


class DepartmentDocument(Base):
    __tablename__ = "department_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="CASCADE", name="department_documents_department_id_fkey"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="pdf")
    pinecone_namespace: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    department: Mapped[Department] = relationship("Department", back_populates="documents")

    __table_args__ = (
        Index("idx_documents_department", "department_id"),
    )


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="SET NULL", name="interview_sessions_department_id_fkey"),
        nullable=True,
    )
    candidate_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_role: Mapped[str] = mapped_column(Text, nullable=False)
    session_type: Mapped[Optional[str]] = mapped_column(Text, server_default="company")
    interaction_mode: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(Text, server_default="active")
    current_phase: Mapped[Optional[str]] = mapped_column(Text, server_default="intro")
    current_question_number: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")
    total_questions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    final_score: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    final_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    engine_version: Mapped[Optional[str]] = mapped_column(Text, server_default="v3")

    organization: Mapped[Optional[Organization]] = relationship("Organization")
    department: Mapped[Department] = relationship("Department", back_populates="sessions")
    messages: Mapped[list[InterviewMessage]] = relationship(
        "InterviewMessage", back_populates="session", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list[InterviewEvaluation]] = relationship(
        "InterviewEvaluation", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_sessions_org", "org_id"),
        Index("idx_sessions_department", "department_id"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_started_at", "started_at"),
        Index("idx_sessions_final_score", "final_score", postgresql_where="final_score IS NOT NULL"),
    )


class InterviewMessage(Base):
    __tablename__ = "interview_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE", name="interview_messages_session_id_fkey"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    question_number: Mapped[Optional[int]] = mapped_column(Integer, server_default="0")
    phase: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    follow_up_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="messages")
    evaluation: Mapped[Optional[InterviewEvaluation]] = relationship(
        "InterviewEvaluation", back_populates="message", uselist=False
    )

    __table_args__ = (
        Index("idx_messages_session", "session_id"),
    )


class InterviewEvaluation(Base):
    __tablename__ = "interview_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE", name="interview_evaluations_session_id_fkey"),
        nullable=False,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_messages.id", ondelete="CASCADE", name="interview_evaluations_message_id_fkey"),
        nullable=False,
    )
    score: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    technical_score: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    communication_score: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weaknesses: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[InterviewSession] = relationship("InterviewSession", back_populates="evaluations")
    message: Mapped[InterviewMessage] = relationship("InterviewMessage", back_populates="evaluation")

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 10", name="interview_evaluations_score_check"),
        Index("idx_evaluations_session_id", "session_id"),
    )


class InterviewTemplate(Base):
    __tablename__ = "interview_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="CASCADE", name="interview_templates_department_id_fkey"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    job_role: Mapped[str] = mapped_column(Text, nullable=False)
    total_questions: Mapped[Optional[int]] = mapped_column(Integer, server_default="10")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    department: Mapped[Department] = relationship("Department", back_populates="templates")


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_token_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    skills: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_data: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_candidate_email", "email"),
        Index("idx_candidate_google", "google_id"),
    )


class CandidateInvitation(Base):
    __tablename__ = "candidate_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    department_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="CASCADE", name="candidate_invitations_department_id_fkey"),
        nullable=False,
    )
    candidate_email: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_name: Mapped[str] = mapped_column(Text, nullable=False)
    job_role: Mapped[str] = mapped_column(Text, nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    interview_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    department: Mapped[Department] = relationship("Department")

    __table_args__ = (
        CheckConstraint("status IN ('pending','accepted','completed','expired')",
                        name="invitations_status_check"),
        Index("idx_invitations_token", "token"),
        Index("idx_invitations_department", "department_id"),
    )


class CandidatePasswordResetToken(Base):
    __tablename__ = "candidate_password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    candidate: Mapped[CandidateProfile] = relationship("CandidateProfile")

    __table_args__ = (
        Index("idx_candidate_reset_tokens_hash", "token_hash"),
        Index("idx_candidate_reset_tokens_candidate", "candidate_id"),
    )


class UserPasswordResetToken(Base):
    __tablename__ = "user_password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship("User")

    __table_args__ = (
        Index("idx_user_reset_tokens_hash", "token_hash"),
        Index("idx_user_reset_tokens_user", "user_id"),
    )


class CandidateSession(Base):
    __tablename__ = "candidate_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_candidate_sessions_candidate", "candidate_id"),
        Index("idx_candidate_sessions_session", "session_id"),
    )


class PublicInterview(Base):
    __tablename__ = "public_interviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("departments.id", ondelete="SET NULL", name="public_interviews_department_id_fkey"),
        nullable=True,
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rich_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interview_mode: Mapped[str] = mapped_column(Text, nullable=False, server_default="typing")
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    verification_method: Mapped[str] = mapped_column(Text, nullable=False, server_default="none")
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_candidates: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skills_required: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    style_name: Mapped[Optional[str]] = mapped_column(Text, server_default="STANDARD")
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped[Organization] = relationship("Organization", back_populates="public_interviews")
    department: Mapped[Optional[Department]] = relationship("Department")
    submissions: Mapped[list[PublicInterviewSubmission]] = relationship(
        "PublicInterviewSubmission", back_populates="public_interview", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_public_interviews_org", "org_id"),
        Index("idx_public_interviews_token", "token"),
        Index("idx_public_interviews_department", "department_id"),
    )


class PublicInterviewSubmission(Base):
    __tablename__ = "public_interview_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public_interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_email: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_name: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    public_interview: Mapped[PublicInterview] = relationship("PublicInterview", back_populates="submissions")
    session: Mapped[InterviewSession] = relationship("InterviewSession")

    __table_args__ = (
        Index("idx_submissions_public", "public_id"),
    )


class InterviewSlot(Base):
    __tablename__ = "interview_slots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False, server_default="45")
    buffer_min: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    organization: Mapped[Organization] = relationship("Organization", back_populates="interview_slots")
    availability: Mapped[list[SlotAvailability]] = relationship(
        "SlotAvailability", back_populates="slot", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_slots_org", "org_id"),
    )


class SlotAvailability(Base):
    __tablename__ = "slot_availability"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    start_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    end_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    slot: Mapped[InterviewSlot] = relationship("InterviewSlot", back_populates="availability")
    booking: Mapped[Optional[Booking]] = relationship(
        "Booking", back_populates="availability", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_availability_slot_date", "slot_id", "date"),
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_slots.id", ondelete="CASCADE"),
        nullable=False,
    )
    availability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("slot_availability.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_email: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_name: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="confirmed")
    confirmation_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    booked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    slot: Mapped[InterviewSlot] = relationship("InterviewSlot")
    availability: Mapped[SlotAvailability] = relationship("SlotAvailability", back_populates="booking")

    __table_args__ = (
        CheckConstraint("status IN ('confirmed','completed','cancelled','no-show')",
                        name="bookings_status_check"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_audit_org", "org_id"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_created", "created_at"),
    )


# ============================================================================
# v4 Evidence-Driven Interview Models
# ============================================================================


class EvidenceStore(Base):
    __tablename__ = "evidence_store"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    competency: Mapped[str] = mapped_column(Text, nullable=False)
    dimension: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_question: Mapped[str] = mapped_column(Text, nullable=False)
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hypothesis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    hypothesis_relevance: Mapped[Optional[float]] = mapped_column(nullable=True)
    evidence_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 10", name="evidence_score_check"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="evidence_confidence_check"),
        CheckConstraint(
            "dimension IN ('technical','communication','reasoning','behavioral','confidence','completeness')",
            name="evidence_dimension_check",
        ),
        Index("idx_evidence_session", "session_id"),
        Index("idx_evidence_session_competency", "session_id", "competency"),
        Index("idx_evidence_session_dimension", "session_id", "dimension"),
        Index("idx_evidence_hypothesis", "hypothesis_id"),
    )


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    supporting_evidence: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, nullable=True
    )
    contradicting_evidence: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="untested")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("direction IN ('positive', 'negative')", name="hypothesis_direction_check"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="hypothesis_confidence_check"),
        CheckConstraint(
            "status IN ('untested', 'testing', 'confirmed', 'refuted')",
            name="hypothesis_status_check",
        ),
        Index("idx_hypotheses_session", "session_id"),
        Index("idx_hypotheses_session_status", "session_id", "status"),
    )


class InterviewObjective(Base):
    __tablename__ = "interview_objectives"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    competency: Mapped[str] = mapped_column(Text, nullable=False)
    dimension: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    hypothesis_statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hypothesis_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    evidence_ids: Mapped[Optional[list]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), default=list, nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'probed', 'satisfied')",
            name="objective_status_check",
        ),
        Index("idx_objectives_session", "session_id"),
        Index("idx_objectives_session_status", "session_id", "status"),
    )


class ConsistencyCheck(Base):
    __tablename__ = "consistency_checks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension: Mapped[str] = mapped_column(Text, nullable=False)
    answers_compared: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    consistency_score: Mapped[float] = mapped_column(nullable=False)
    contradictions: Mapped[Optional[dict]] = mapped_column(JSONB, default=list, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "consistency_score >= 0 AND consistency_score <= 1",
            name="consistency_score_check",
        ),
        Index("idx_consistency_session", "session_id"),
    )


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_signal: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("value >= 0 AND value <= 1", name="observation_value_check"),
        Index("idx_observations_session", "session_id"),
        Index("idx_observations_session_type", "session_id", "type"),
    )


class CandidateSavedListing(Base):
    __tablename__ = "candidate_saved_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("public_interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("candidate_id", "listing_id", name="uq_candidate_listing"),
        Index("idx_saved_listings_candidate", "candidate_id"),
    )


class ScorecardTemplate(Base):
    __tablename__ = "scorecard_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    competencies: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped[Organization] = relationship("Organization")

    __table_args__ = (
        Index("idx_scorecard_templates_org", "org_id"),
    )


class ScorecardResult(Base):
    __tablename__ = "scorecard_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scorecard_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    weighted_score: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped[InterviewSession] = relationship("InterviewSession")

    __table_args__ = (
        Index("idx_scorecard_results_session", "session_id"),
    )
