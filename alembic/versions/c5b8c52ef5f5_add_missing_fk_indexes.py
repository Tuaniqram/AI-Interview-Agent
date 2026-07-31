"""add_missing_fk_indexes

Revision ID: c5b8c52ef5f5
Revises: a1b2c3d4e5f6
Create Date: 2026-07-30 13:45:22.184591
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5b8c52ef5f5'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_bookings_slot', 'bookings', ['slot_id'])
    op.create_index('idx_bookings_availability', 'bookings', ['availability_id'])
    op.create_index('idx_org_invitations_org', 'org_invitations', ['org_id'])
    op.create_index('idx_org_invitations_inviter', 'org_invitations', ['inviter_id'])
    op.create_index('idx_org_users_invited_by', 'org_users', ['invited_by'])
    op.create_index('idx_evaluations_message', 'interview_evaluations', ['message_id'])
    op.create_index('idx_templates_department', 'interview_templates', ['department_id'])
    op.create_index('idx_invitations_created_by', 'candidate_invitations', ['created_by'])
    op.create_index('idx_public_interviews_template', 'public_interviews', ['template_id'])
    # CandidateSavedListing model not yet migrated to production — index added in __table_args__


def downgrade() -> None:
    op.drop_index('idx_bookings_slot', table_name='bookings')
    op.drop_index('idx_bookings_availability', table_name='bookings')
    op.drop_index('idx_org_invitations_org', table_name='org_invitations')
    op.drop_index('idx_org_invitations_inviter', table_name='org_invitations')
    op.drop_index('idx_org_users_invited_by', table_name='org_users')
    op.drop_index('idx_evaluations_message', table_name='interview_evaluations')
    op.drop_index('idx_templates_department', table_name='interview_templates')
    op.drop_index('idx_invitations_created_by', table_name='candidate_invitations')
    op.drop_index('idx_public_interviews_template', table_name='public_interviews')
