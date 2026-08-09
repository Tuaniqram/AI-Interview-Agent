"""add_calibration_feedback

T4 calibration loop — recruiter-recorded post-hire outcome vs the session's
predicted (calibrated) verdict. Predicted values are snapshotted into this row
when feedback is recorded (read from ``interview_brain.brain_metadata``).

Revision ID: b1a2c3d4e5f6
Revises: a1b2f1a2b3c4
Create Date: 2026-08-09 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, None] = 'a1b2f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('calibration_feedback',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('org_id', sa.UUID(), nullable=True),
    sa.Column('department_id', sa.BigInteger(), nullable=True),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('job_role', sa.Text(), nullable=True),
    sa.Column('predicted_verdict', sa.Text(), nullable=True),
    sa.Column('predicted_score', sa.Numeric(), nullable=True),
    sa.Column('difficulty_reached', sa.Integer(), nullable=True),
    sa.Column('role_floor', sa.Integer(), nullable=True),
    sa.Column('actual_outcome', sa.Text(), server_default='no_feedback', nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id')
    )
    op.create_index('idx_calibration_feedback_org', 'calibration_feedback', ['org_id'], unique=False)
    op.create_index('idx_calibration_feedback_recorded', 'calibration_feedback', ['recorded_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_calibration_feedback_recorded', table_name='calibration_feedback')
    op.drop_index('idx_calibration_feedback_org', table_name='calibration_feedback')
    op.drop_table('calibration_feedback')
