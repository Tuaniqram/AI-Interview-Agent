"""add_scorecard_tables

Revision ID: 337d650bfde8
Revises: f6a7b8c9d0e1
Create Date: 2026-07-27 02:17:23.749092
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '337d650bfde8'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('scorecard_templates',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('org_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('competencies', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scorecard_templates_org', 'scorecard_templates', ['org_id'], unique=False)
    op.create_table('scorecard_results',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('template_id', sa.UUID(), nullable=True),
    sa.Column('scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('weighted_score', sa.Numeric(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['template_id'], ['scorecard_templates.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scorecard_results_session', 'scorecard_results', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_scorecard_results_session', table_name='scorecard_results')
    op.drop_table('scorecard_results')
    op.drop_index('idx_scorecard_templates_org', table_name='scorecard_templates')
    op.drop_table('scorecard_templates')
