"""unify accounts, step 2: copy candidates into users (idempotent; the old tables are kept)

Revision ID: e5b6c7d8f9a0
Revises: d4a5b6c7e8f9
Create Date: 2026-11-20

Plan: docs/UNIFIED_USER_ACCOUNTS_PLAN.md. Copies, never moves: candidate_profiles, candidate_refresh_tokens and
candidate_password_reset_tokens keep every row until the clean-up migration, so this can be undone and re-run.

* Each candidate becomes a users row with the SAME id, so every table that points at candidate_profiles.id stays valid.
* Candidate refresh tokens keep their ids and hashes (signed-in candidates stay signed in) and are marked
  actor='candidate'; password reset tokens keep their ids and hashes.
* Safe to run again after the new code is deployed: it only copies what is not there yet, which picks up any candidate
  the old code registered in the gap between this migration and the deploy.
* It refuses to run, and changes nothing, if a candidate's email already belongs to a DIFFERENT users row: merging two
  accounts by email alone is an account-takeover route, so that is always a manual decision.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5b6c7d8f9a0"
down_revision: Union[str, None] = "d4a5b6c7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    clashes = conn.execute(sa.text(
        "select c.id::text, u.id::text from candidate_profiles c "
        "join users u on lower(u.email) = lower(c.email) and u.id <> c.id"
    )).all()
    if clashes:
        raise RuntimeError(
            f"{len(clashes)} candidate(s) share an email with a different users row (candidate id, user id): "
            + ", ".join(f"{a[:8]}/{b[:8]}" for a, b in clashes[:5])
            + ". Resolve these by hand; they are never merged automatically."
        )

    # Remembers exactly which users rows this migration created, so the downgrade removes only those.
    op.execute("CREATE TABLE IF NOT EXISTS unify_users_migration_log (candidate_id uuid PRIMARY KEY, copied_at timestamptz NOT NULL DEFAULT now())")

    op.execute("""
        WITH moved AS (
            INSERT INTO users (id, email, password_hash, name, is_admin, is_active, is_registered, is_verified, verified_at,
                               verification_token_hash, verification_sent_at, google_id, created_at, updated_at)
            SELECT c.id, c.email, c.password_hash, c.name, false, true, c.is_registered, c.is_verified, c.verified_at,
                   c.verification_token_hash, c.verification_sent_at, c.google_id, c.created_at, c.updated_at
            FROM candidate_profiles c
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = c.id)
            RETURNING id
        )
        INSERT INTO unify_users_migration_log (candidate_id) SELECT id FROM moved
    """)

    op.execute("""
        INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, revoked, created_at, actor)
        SELECT t.id, t.candidate_id, t.token_hash, t.expires_at, t.revoked, t.created_at, 'candidate'
        FROM candidate_refresh_tokens t
        WHERE NOT EXISTS (SELECT 1 FROM refresh_tokens r WHERE r.id = t.id)
    """)

    op.execute("""
        INSERT INTO user_password_reset_tokens (id, user_id, token_hash, expires_at, used, created_at)
        SELECT t.id, t.candidate_id, t.token_hash, t.expires_at, t.used, t.created_at
        FROM candidate_password_reset_tokens t
        WHERE NOT EXISTS (SELECT 1 FROM user_password_reset_tokens r WHERE r.id = t.id)
    """)


def downgrade() -> None:
    # Tokens first (they point at users), then only the users rows this migration created.
    op.execute("DELETE FROM user_password_reset_tokens WHERE id IN (SELECT id FROM candidate_password_reset_tokens)")
    op.execute("DELETE FROM refresh_tokens WHERE actor = 'candidate' AND id IN (SELECT id FROM candidate_refresh_tokens)")
    op.execute("DELETE FROM users WHERE id IN (SELECT candidate_id FROM unify_users_migration_log)")
    op.execute("DROP TABLE IF EXISTS unify_users_migration_log")
