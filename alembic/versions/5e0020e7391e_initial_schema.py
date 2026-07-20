"""baseline — stamp existing schema as starting point

Revision ID: 5e0020e7391e
Revises:
Create Date: 2026-07-20 18:10:02.651009

NOTE: This is a no-op baseline migration for an existing database.
Alembic is being introduced AFTER tables already exist.
Future `alembic revision --autogenerate` will detect only NEW changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '5e0020e7391e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: tables already exist in Supabase.
    # This baseline tells Alembic "schema starts here."
    pass


def downgrade() -> None:
    pass
