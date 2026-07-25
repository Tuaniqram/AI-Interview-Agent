"""add org_invitations table

Revision ID: f6a7b8c9d0e1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-25 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('org_invitations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('inviter_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('role', sa.Text(), nullable=False, server_default='member'),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('idx_org_invitations_token', 'org_invitations', ['token'])
    op.create_index('idx_org_invitations_email', 'org_invitations', ['email'])


def downgrade() -> None:
    op.drop_index('idx_org_invitations_email', table_name='org_invitations')
    op.drop_index('idx_org_invitations_token', table_name='org_invitations')
    op.drop_table('org_invitations')
