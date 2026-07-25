"""add candidate_password_reset_tokens table

Revision ID: e5f6a7b8c9d0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-25 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('candidate_password_reset_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_candidate_reset_tokens_hash', 'candidate_password_reset_tokens', ['token_hash'])
    op.create_index('idx_candidate_reset_tokens_candidate', 'candidate_password_reset_tokens', ['candidate_id'])


def downgrade() -> None:
    op.drop_index('idx_candidate_reset_tokens_candidate', table_name='candidate_password_reset_tokens')
    op.drop_index('idx_candidate_reset_tokens_hash', table_name='candidate_password_reset_tokens')
    op.drop_table('candidate_password_reset_tokens')
