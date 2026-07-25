"""add user_password_reset_tokens table

Revision ID: d5e6f7a8b9c0
Revises: e5f6a7b8c9d0
Create Date: 2026-07-25 21:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_password_reset_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_user_reset_tokens_hash', 'user_password_reset_tokens', ['token_hash'])
    op.create_index('idx_user_reset_tokens_user', 'user_password_reset_tokens', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_user_reset_tokens_user', table_name='user_password_reset_tokens')
    op.drop_index('idx_user_reset_tokens_hash', table_name='user_password_reset_tokens')
    op.drop_table('user_password_reset_tokens')
