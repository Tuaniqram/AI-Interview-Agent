"""
SQLAlchemy ORM models — maps all existing Supabase tables.

These models coexist with the Supabase Python client.
Existing code continues using get_supabase().table(...).
New code can use these models via get_db() dependency.

Constraint/index names match the live Supabase DB exactly so
Alembic autogenerate shows zero diff against existing tables.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    documents: Mapped[list[CompanyDocument]] = relationship(
        "CompanyDocument", back_populates="company", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[InterviewSession]] = relationship(
        "InterviewSession", back_populates="company"
    )
    templates: Mapped[list[InterviewTemplate]] = relationship(
        "InterviewTemplate", back_populates="company", cascade="all, delete-orphan"
    )


class CompanyDocument(Base):
    __tablename__ = "company_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE", name="company_documents_company_id_fkey"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(Text, nullable=False, server_default="pdf")
    pinecone_namespace: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped[Company] = relationship("Company", back_populates="documents")

    __table_args__ = (
        Index("idx_documents_company", "company_id"),
    )


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE", name="interview_sessions_company_id_fkey"),
        nullable=False,
    )
    candidate_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    candidate_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True, server_default="")
    candidate_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True, server_default="")
    job_role: Mapped[str] = mapped_column(Text, nullable=False)
    interview_type: Mapped[Optional[str]] = mapped_column(Text, server_default="company")
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

    company: Mapped[Company] = relationship("Company", back_populates="sessions")
    messages: Mapped[list[InterviewMessage]] = relationship(
        "InterviewMessage", back_populates="session", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list[InterviewEvaluation]] = relationship(
        "InterviewEvaluation", back_populates="session", cascade="all, delete-orphan"
    )
    progress: Mapped[list[UserProgress]] = relationship(
        "UserProgress", back_populates="session"
    )

    __table_args__ = (
        Index("idx_sessions_company", "company_id"),
        Index("idx_sessions_company_id", "company_id"),
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
        Index("idx_messages_session_id", "session_id"),
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
    company_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("companies.id", ondelete="CASCADE", name="interview_templates_company_id_fkey"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    job_role: Mapped[str] = mapped_column(Text, nullable=False)
    total_questions: Mapped[Optional[int]] = mapped_column(Integer, server_default="10")
    interview_type: Mapped[Optional[str]] = mapped_column(Text, server_default="company")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    company: Mapped[Company] = relationship("Company", back_populates="templates")


class UserProgress(Base):
    __tablename__ = "user_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE", name="user_progress_session_id_fkey"),
        nullable=True,
    )
    candidate_identifier: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    average_score: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    total_questions_answered: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    questions_correct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    strengths_improvement_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped[Optional[InterviewSession]] = relationship("InterviewSession", back_populates="progress")
