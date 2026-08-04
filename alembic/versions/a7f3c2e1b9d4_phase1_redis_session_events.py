"""phase1: checkpoint version, event log, saved-listings drift fix

Revision ID: a7f3c2e1b9d4
Revises: d6e7f8a9b0c1
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "a7f3c2e1b9d4"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # --- checkpoint concurrency token on existing v4_session_state ---
    op.add_column(
        "v4_session_state",
        sa.Column("state_version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_v4_session_state_state_version", "v4_session_state", ["state_version"]
    )

    # --- event log for the v4 answer pipeline (own best-effort writer) ---
    op.create_table(
        "interview_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("payload", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["interview_sessions.id"],
            name="fk_interview_events_session",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "session_id", "seq", name="uq_interview_events_session_seq"
        ),
    )
    op.create_index(
        "ix_interview_events_session_seq",
        "interview_events",
        ["session_id", "seq"],
    )
    op.create_index("ix_interview_events_type", "interview_events", ["event_type"])
    op.create_index(
        "ix_interview_events_created", "interview_events", ["created_at"]
    )

    # --- drift fix: candidate_saved_listings was missing from the live DB;
    # the model declared listing_id as Integer FK -> public_interviews.id
    # (uuid), a type mismatch. Create the table with the correct UUID FK. ---
    op.create_table(
        "candidate_saved_listings",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("candidate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.id"],
            name="fk_saved_listings_candidate",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["public_interviews.id"],
            name="fk_saved_listings_listing",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "candidate_id", "listing_id", name="uq_candidate_listing"
        ),
    )
    op.create_index(
        "idx_saved_listings_candidate", "candidate_saved_listings", ["candidate_id"]
    )
    op.create_index(
        "idx_saved_listings_listing", "candidate_saved_listings", ["listing_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_saved_listings_listing", table_name="candidate_saved_listings")
    op.drop_index("idx_saved_listings_candidate", table_name="candidate_saved_listings")
    op.drop_table("candidate_saved_listings")

    op.drop_index("ix_interview_events_created", table_name="interview_events")
    op.drop_index("ix_interview_events_type", table_name="interview_events")
    op.drop_index("ix_interview_events_session_seq", table_name="interview_events")
    op.drop_table("interview_events")

    op.drop_index("ix_v4_session_state_state_version", table_name="v4_session_state")
    op.drop_column("v4_session_state", "state_version")
