"""allow practice sessions without an organization

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-11-06
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE interview_sessions ALTER COLUMN org_id DROP NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE interview_sessions ALTER COLUMN org_id SET NOT NULL")
