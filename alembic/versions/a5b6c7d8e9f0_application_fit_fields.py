"""add automatic fit-evaluation fields to public_interview_submissions

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-11-06

Additive only: existing rows are preserved and backfilled with
fit_status = 'pending' via the column default.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE public_interview_submissions "
        "ADD COLUMN IF NOT EXISTS fit_status TEXT NOT NULL DEFAULT 'pending'"
    )
    op.execute(
        "ALTER TABLE public_interview_submissions "
        "ADD COLUMN IF NOT EXISTS fit_breakdown JSONB"
    )
    op.execute(
        "ALTER TABLE public_interview_submissions "
        "ADD COLUMN IF NOT EXISTS fit_evaluated_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE public_interview_submissions "
        "ADD COLUMN IF NOT EXISTS fit_error TEXT"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public_interview_submissions DROP COLUMN IF EXISTS fit_error")
    op.execute("ALTER TABLE public_interview_submissions DROP COLUMN IF EXISTS fit_evaluated_at")
    op.execute("ALTER TABLE public_interview_submissions DROP COLUMN IF EXISTS fit_breakdown")
    op.execute("ALTER TABLE public_interview_submissions DROP COLUMN IF EXISTS fit_status")
