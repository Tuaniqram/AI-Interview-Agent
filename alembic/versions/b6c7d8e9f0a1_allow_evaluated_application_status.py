"""allow the 'evaluated' application status and constrain fit_status

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-11-06

The automatic fit evaluation moves an application from 'applied' to
'evaluated'. Loosens the status CHECK (every existing row still satisfies it) and adds a
CHECK on the new fit_status column (existing rows are all 'pending').
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b6c7d8e9f0a1"
down_revision: Union[str, None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT = "public_interview_submissions_status_check"
_TABLE = "public_interview_submissions"
_WITH_EVALUATED = (
    "'applied', 'screening', 'evaluated', 'interview_offered', 'interview_accepted', "
    "'interview_declined', 'interviewed', 'hired', 'rejected', 'withdrawn'"
)
_WITHOUT_EVALUATED = (
    "'applied', 'screening', 'interview_offered', 'interview_accepted', "
    "'interview_declined', 'interviewed', 'hired', 'rejected', 'withdrawn'"
)


_FIT_CONSTRAINT = "public_interview_submissions_fit_status_check"
_FIT_VALUES = "'pending', 'running', 'completed', 'failed'"


def upgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.execute(f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} CHECK (status IN ({_WITH_EVALUATED}))")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_FIT_CONSTRAINT}")
    op.execute(f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_FIT_CONSTRAINT} CHECK (fit_status IN ({_FIT_VALUES}))")


def downgrade() -> None:
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_FIT_CONSTRAINT}")
    # Rows already marked 'evaluated' fall back to 'screening' so the stricter check holds.
    op.execute(f"UPDATE {_TABLE} SET status = 'screening' WHERE status = 'evaluated'")
    op.execute(f"ALTER TABLE {_TABLE} DROP CONSTRAINT IF EXISTS {_CONSTRAINT}")
    op.execute(f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_CONSTRAINT} CHECK (status IN ({_WITHOUT_EVALUATED}))")
