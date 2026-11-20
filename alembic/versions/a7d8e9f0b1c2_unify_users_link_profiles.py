"""unify accounts, step 3b: link candidate_profiles to users (apply AFTER the new code is deployed)

Revision ID: a7d8e9f0b1c2
Revises: f6c7d8e9a0b1
Create Date: 2026-11-20

Plan: docs/UNIFIED_USER_ACCOUNTS_PLAN.md. Run once the new code is live:

1. Copies any candidate that the PREVIOUS code registered between step 2 and the deploy (the same idempotent copy as step 2).
2. Adds the foreign key candidate_profiles.id -> users.id (cascade), so a candidate profile can never exist without its account.

It is not applied earlier because, until the new code is running, the previous code still inserts candidate_profiles rows
without a users row, and the foreign key would make those registrations fail.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7d8e9f0b1c2"
down_revision: Union[str, None] = "f6c7d8e9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    clashes = conn.execute(sa.text(
        "select count(*) from candidate_profiles c join users u on lower(u.email) = lower(c.email) and u.id <> c.id "
        "where c.email is not null"
    )).scalar()
    if clashes:
        raise RuntimeError(f"{clashes} candidate(s) share an email with a different users row; resolve by hand")

    op.execute("CREATE TABLE IF NOT EXISTS unify_users_migration_log (candidate_id uuid PRIMARY KEY, copied_at timestamptz NOT NULL DEFAULT now())")
    op.execute("""
        WITH moved AS (
            INSERT INTO users (id, email, password_hash, name, is_admin, is_active, is_registered, is_verified, verified_at,
                               verification_token_hash, verification_sent_at, google_id, created_at, updated_at)
            SELECT c.id, c.email, c.password_hash, c.name, false, true, coalesce(c.is_registered, false), coalesce(c.is_verified, false),
                   c.verified_at, c.verification_token_hash, c.verification_sent_at, c.google_id, c.created_at, c.updated_at
            FROM candidate_profiles c
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = c.id) AND c.email IS NOT NULL
            RETURNING id
        )
        INSERT INTO unify_users_migration_log (candidate_id) SELECT id FROM moved
    """)
    op.execute("""
        INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, revoked, created_at, actor)
        SELECT t.id, t.candidate_id, t.token_hash, t.expires_at, t.revoked, t.created_at, 'candidate'
        FROM candidate_refresh_tokens t
        WHERE NOT EXISTS (SELECT 1 FROM refresh_tokens r WHERE r.id = t.id)
          AND EXISTS (SELECT 1 FROM users u WHERE u.id = t.candidate_id)
    """)
    op.execute("""
        INSERT INTO user_password_reset_tokens (id, user_id, token_hash, expires_at, used, created_at)
        SELECT t.id, t.candidate_id, t.token_hash, t.expires_at, t.used, t.created_at
        FROM candidate_password_reset_tokens t
        WHERE NOT EXISTS (SELECT 1 FROM user_password_reset_tokens r WHERE r.id = t.id)
          AND EXISTS (SELECT 1 FROM users u WHERE u.id = t.candidate_id)
    """)

    orphans = conn.execute(sa.text(
        "select count(*) from candidate_profiles c where not exists (select 1 from users u where u.id = c.id)"
    )).scalar()
    if orphans:
        raise RuntimeError(f"{orphans} candidate profile(s) still have no users row; cannot add the foreign key")

    op.execute(
        "ALTER TABLE candidate_profiles ADD CONSTRAINT candidate_profiles_id_users_fkey "
        "FOREIGN KEY (id) REFERENCES users (id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE candidate_profiles DROP CONSTRAINT IF EXISTS candidate_profiles_id_users_fkey")
