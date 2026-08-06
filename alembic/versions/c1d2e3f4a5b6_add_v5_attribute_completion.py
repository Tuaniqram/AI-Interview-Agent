"""add_v5_attribute_completion

Additive columns completing the V5 tables:
- hypotheses.competency           (saturation + competency-scoped targeting)
- bundle tables .snapshot JSONB   (raw bundle kept alongside mapped columns)
- consistency_checks mapped columns (check_type/assessment/score/confidence/evidence/checked_at)

Revision ID: c1d2e3f4a5b6
Revises: b7c9d1e2f3a4
Create Date: 2026-08-05 12:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b7c9d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hypotheses', sa.Column('competency', sa.Text(), nullable=True))

    for table in (
        'company_brains',
        'scorecards',
        'interview_blueprints',
        'candidate_brains',
        'candidate_evidence_requirements',
    ):
        op.add_column(
            table,
            sa.Column(
                'snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
        )

    op.add_column('consistency_checks', sa.Column('check_type', sa.Text(), nullable=True))
    op.add_column('consistency_checks', sa.Column('assessment', sa.Text(), nullable=True))
    op.add_column('consistency_checks', sa.Column('score', sa.Float(), nullable=True))
    op.add_column('consistency_checks', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column(
        'consistency_checks',
        sa.Column(
            'evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        'consistency_checks',
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('consistency_checks', 'checked_at')
    op.drop_column('consistency_checks', 'evidence')
    op.drop_column('consistency_checks', 'confidence')
    op.drop_column('consistency_checks', 'score')
    op.drop_column('consistency_checks', 'assessment')
    op.drop_column('consistency_checks', 'check_type')

    for table in (
        'candidate_evidence_requirements',
        'candidate_brains',
        'interview_blueprints',
        'scorecards',
        'company_brains',
    ):
        op.drop_column(table, 'snapshot')

    op.drop_column('hypotheses', 'competency')
