"""one owner user per organization

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-11-06

Drops org_users, org_invitations, and candidate_sessions.
Adds organizations.owner_user_id and backfills it from the existing owner.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE organizations ADD COLUMN owner_user_id uuid")
    op.execute(
        """
        UPDATE organizations o
        SET owner_user_id = sub.user_id
        FROM (
            SELECT DISTINCT ON (org_id) org_id, user_id
            FROM org_users
            ORDER BY org_id, (role = 'owner') DESC, joined_at ASC
        ) sub
        WHERE o.id = sub.org_id
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM organizations WHERE owner_user_id IS NULL) THEN
                ALTER TABLE organizations ALTER COLUMN owner_user_id SET NOT NULL;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        ALTER TABLE organizations
            ADD CONSTRAINT organizations_owner_user_id_fkey
            FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE RESTRICT
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_organizations_owner_user_id ON organizations (owner_user_id)"
    )
    op.execute("DROP TABLE IF EXISTS org_users CASCADE")
    op.execute("DROP TABLE IF EXISTS org_invitations CASCADE")
    op.execute("DROP TABLE IF EXISTS candidate_sessions CASCADE")


def downgrade() -> None:
    raise NotImplementedError("One-owner organization reduction is not reversible")
