"""enhance_interview_templates

Revision ID: 700b2c9a5533
Revises: 337d650bfde8
Create Date: 2026-07-27 02:34:16.430600
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '700b2c9a5533'
down_revision: Union[str, None] = '337d650bfde8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('interview_templates', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('interview_templates', sa.Column('interview_style', sa.Text(), server_default='STANDARD', nullable=True))
    op.add_column('interview_templates', sa.Column('competencies', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('interview_templates', 'competencies')
    op.drop_column('interview_templates', 'interview_style')
    op.drop_column('interview_templates', 'description')
