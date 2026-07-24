"""add style_name to public_interviews

Revision ID: c3d4e5f6a7b8
Revises: b2a1c3d4e5f6
Create Date: 2026-07-24 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2a1c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "public_interviews",
        sa.Column("style_name", sa.Text(), server_default="STANDARD", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("public_interviews", "style_name")
