"""allow saturated hypotheses, summary phase, and the session template link

Revision ID: c1a2b3c4d5e6
Revises: b6c7d8e9f0a1
Create Date: 2026-11-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1a2b3c4d5e6"
down_revision: Union[str, None] = "b6c7d8e9f0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The hypothesis engine has a fourth settled state ("saturated") that the
    # original check constraint never allowed, which made finalize persistence fail.
    op.execute("ALTER TABLE hypotheses DROP CONSTRAINT IF EXISTS hypotheses_status_check")
    op.execute("ALTER TABLE hypotheses DROP CONSTRAINT IF EXISTS hypothesis_status_check")
    op.execute(
        "ALTER TABLE hypotheses ADD CONSTRAINT hypotheses_status_check "
        "CHECK (status IN ('untested', 'testing', 'confirmed', 'refuted', 'saturated'))"
    )

    # Completion sets the phase to "summary"; the old constraint stopped at "conclusion".
    op.execute("ALTER TABLE interview_sessions DROP CONSTRAINT IF EXISTS interview_sessions_current_phase_check")
    op.execute(
        "ALTER TABLE interview_sessions ADD CONSTRAINT interview_sessions_current_phase_check "
        "CHECK (current_phase IN ('intro', 'experience', 'technical', 'behavioral', 'conclusion', 'summary'))"
    )

    # Keep the exact listing template that produced a session, so its competencies
    # are used instead of whichever org template happens to be newest.
    op.add_column("interview_sessions", sa.Column("template_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "interview_sessions_template_id_fkey",
        "interview_sessions",
        "interview_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_interview_sessions_template", "interview_sessions", ["template_id"])


def downgrade() -> None:
    op.drop_index("idx_interview_sessions_template", table_name="interview_sessions")
    op.drop_constraint("interview_sessions_template_id_fkey", "interview_sessions", type_="foreignkey")
    op.drop_column("interview_sessions", "template_id")

    op.execute("ALTER TABLE interview_sessions DROP CONSTRAINT IF EXISTS interview_sessions_current_phase_check")
    op.execute(
        "ALTER TABLE interview_sessions ADD CONSTRAINT interview_sessions_current_phase_check "
        "CHECK (current_phase IN ('intro', 'experience', 'technical', 'behavioral', 'conclusion'))"
    )

    op.execute("ALTER TABLE hypotheses DROP CONSTRAINT IF EXISTS hypotheses_status_check")
    op.execute("ALTER TABLE hypotheses DROP CONSTRAINT IF EXISTS hypothesis_status_check")
    op.execute(
        "ALTER TABLE hypotheses ADD CONSTRAINT hypotheses_status_check "
        "CHECK (status IN ('untested', 'testing', 'confirmed', 'refuted'))"
    )
