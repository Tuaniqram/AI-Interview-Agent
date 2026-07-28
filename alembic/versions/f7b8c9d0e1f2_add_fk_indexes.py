"""add FK indexes for performance

Revision ID: f7b8c9d0e1f2
Revises: 700b2c9a5533
Create Date: 2026-07-28 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f7b8c9d0e1f2"
down_revision: Union[str, None] = "700b2c9a5533"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_refresh_tokens_user", "refresh_tokens", ["user_id"])
    op.create_index("idx_interview_sessions_candidate_profile", "interview_sessions", ["candidate_profile_id"])
    op.create_index("idx_public_submissions_session", "public_interview_submissions", ["session_id"])
    op.create_index("idx_bookings_session", "bookings", ["session_id"])
    op.create_index("idx_scorecard_results_template", "scorecard_results", ["template_id"])

    op.add_column("interview_sessions", sa.Column("scorecard_template_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_interview_sessions_scorecard_template", "interview_sessions", "scorecard_templates", ["scorecard_template_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_interview_sessions_scorecard_template", "interview_sessions", ["scorecard_template_id"])

    op.add_column("interview_templates", sa.Column("scorecard_template_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_interview_templates_scorecard_template", "interview_templates", "scorecard_templates", ["scorecard_template_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_interview_templates_scorecard_template", "interview_templates", ["scorecard_template_id"])


def downgrade() -> None:
    op.drop_index("idx_scorecard_results_template", table_name="scorecard_results")
    op.drop_index("idx_bookings_session", table_name="bookings")
    op.drop_index("idx_public_submissions_session", table_name="public_interview_submissions")
    op.drop_index("idx_refresh_tokens_user", table_name="refresh_tokens")
    op.drop_index("idx_interview_sessions_candidate_profile", table_name="interview_sessions")

    op.drop_index("idx_interview_sessions_scorecard_template", table_name="interview_sessions")
    op.drop_constraint("fk_interview_sessions_scorecard_template", "interview_sessions", type_="foreignkey")
    op.drop_column("interview_sessions", "scorecard_template_id")

    op.drop_index("idx_interview_templates_scorecard_template", table_name="interview_templates")
    op.drop_constraint("fk_interview_templates_scorecard_template", "interview_templates", type_="foreignkey")
    op.drop_column("interview_templates", "scorecard_template_id")
