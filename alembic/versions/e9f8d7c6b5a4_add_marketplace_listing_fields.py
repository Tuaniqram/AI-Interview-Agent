"""add department_id, starts_at, expires_at, skills_required, rich_description to public_interviews

Revision ID: e9f8d7c6b5a4
Revises: d4e5f6a7b8c9
Create Date: 2026-07-23 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e9f8d7c6b5a4'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('public_interviews', sa.Column('department_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f('public_interviews_department_id_fkey'),
        'public_interviews', 'departments',
        ['department_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('idx_public_interviews_department', 'public_interviews', ['department_id'])
    op.add_column('public_interviews', sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('public_interviews', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('public_interviews', sa.Column('skills_required', sa.Text(), nullable=True))
    op.add_column('public_interviews', sa.Column('rich_description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('public_interviews', 'rich_description')
    op.drop_column('public_interviews', 'skills_required')
    op.drop_column('public_interviews', 'expires_at')
    op.drop_column('public_interviews', 'starts_at')
    op.drop_index('idx_public_interviews_department', 'public_interviews')
    op.drop_constraint(
        op.f('public_interviews_department_id_fkey'), 'public_interviews', type_='foreignkey'
    )
    op.drop_column('public_interviews', 'department_id')
