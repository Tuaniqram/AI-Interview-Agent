"""drop_unused_indexes

Revision ID: d6e7f8a9b0c1
Revises: c5b8c52ef5f5
Create Date: 2026-07-31 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6e7f8a9b0c1'
down_revision: Union[str, None] = 'c5b8c52ef5f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Redundant — unique constraints already create backing indexes
    op.drop_index('idx_org_invitations_token', table_name='org_invitations')
    op.drop_index('idx_invitations_token', table_name='candidate_invitations')
    op.drop_index('idx_public_interviews_token', table_name='public_interviews')
    # Never used by queries (verified against app code)
    op.drop_index('idx_candidate_google', table_name='candidate_profiles')
    op.drop_index('idx_public_interviews_department', table_name='public_interviews')
    # Dead tables — models exist but no code reads or writes them
    op.drop_index('idx_hypotheses_session', table_name='hypotheses')
    op.drop_index('idx_hypotheses_session_status', table_name='hypotheses')
    op.drop_index('idx_observations_session', table_name='observations')
    op.drop_index('idx_observations_session_type', table_name='observations')
    op.drop_index('idx_objectives_session', table_name='interview_objectives')
    op.drop_index('idx_objectives_session_status', table_name='interview_objectives')
    op.drop_index('idx_consistency_session', table_name='consistency_checks')


def downgrade() -> None:
    op.create_index('idx_consistency_session', 'consistency_checks', ['session_id'])
    op.create_index('idx_objectives_session_status', 'interview_objectives', ['session_id', 'status'])
    op.create_index('idx_objectives_session', 'interview_objectives', ['session_id'])
    op.create_index('idx_observations_session_type', 'observations', ['session_id', 'type'])
    op.create_index('idx_observations_session', 'observations', ['session_id'])
    op.create_index('idx_hypotheses_session_status', 'hypotheses', ['session_id', 'status'])
    op.create_index('idx_hypotheses_session', 'hypotheses', ['session_id'])
    op.create_index('idx_public_interviews_department', 'public_interviews', ['department_id'])
    op.create_index('idx_candidate_google', 'candidate_profiles', ['google_id'])
    op.create_index('idx_public_interviews_token', 'public_interviews', ['token'])
    op.create_index('idx_invitations_token', 'candidate_invitations', ['token'])
    op.create_index('idx_org_invitations_token', 'org_invitations', ['token'])
