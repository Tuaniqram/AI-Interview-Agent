"""add_role_profiler_cache

Adds ``interview_templates.suggested_competencies`` — the DB-backed cache for
the role-first AI competency profiler (F1).

Revision ID: a1b2f1a2b3c4
Revises: 337d650bfde8
Create Date: 2026-08-07 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1b2f1a2b3c4'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'interview_templates',
        sa.Column('suggested_competencies', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('interview_templates', 'suggested_competencies')
