"""add engine_version to interview_sessions

Revision ID: b2a1c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-07-24 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2a1c3d4e5f6"
down_revision: Union[str, None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("engine_version", sa.Text(), server_default="v3", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interview_sessions", "engine_version")
