"""add verification_token_hash, verification_sent_at to candidate_profiles

Revision ID: d4e5f6a7b8c9
Revises: a3c8b7d1e9f0
Create Date: 2026-07-23 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'a3c8b7d1e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('candidate_profiles', sa.Column('verification_token_hash', sa.Text(), nullable=True))
    op.add_column('candidate_profiles', sa.Column('verification_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('candidate_profiles', 'verification_sent_at')
    op.drop_column('candidate_profiles', 'verification_token_hash')
