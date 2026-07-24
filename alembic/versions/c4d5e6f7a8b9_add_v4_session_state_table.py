"""add v4_session_state table for DB-backed session store

Revision ID: c4d5e6f7a8b9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-24 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "v4_session_state",
        sa.Column("session_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("state", JSONB, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["session_id"], ["interview_sessions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_v4_session_state_updated_at",
                    "v4_session_state", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_v4_session_state_updated_at")
    op.drop_table("v4_session_state")
