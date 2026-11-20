"""unify accounts, step 5: drop the legacy candidate token tables and the identity columns on candidate_profiles

Revision ID: b8e9f0a1b2c3
Revises: a7d8e9f0b1c2
Create Date: 2026-11-20

Plan: docs/UNIFIED_USER_ACCOUNTS_PLAN.md. Apply only after the unified-accounts code has been live and verified: from here on there
is no copy of the old identity left to roll back to except the JSON backup and this migration's downgrade (which rebuilds the old
shape from `users` / `refresh_tokens` / `user_password_reset_tokens`).

After this migration candidate_profiles holds only candidate data (phone, resume, skills, profile data), keyed by users.id.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8e9f0a1b2c3"
down_revision: Union[str, None] = "a7d8e9f0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_COLUMNS = (
    "email", "name", "password_hash", "google_id", "is_registered", "is_verified",
    "verified_at", "verification_token_hash", "verification_sent_at",
)


def upgrade() -> None:
    conn = op.get_bind()
    orphans = conn.execute(sa.text(
        "select count(*) from candidate_profiles c where not exists (select 1 from users u where u.id = c.id)"
    )).scalar()
    if orphans:
        raise RuntimeError(f"{orphans} candidate profile(s) have no users row; refusing to drop their only identity")

    op.execute("DROP TABLE IF EXISTS candidate_refresh_tokens")
    op.execute("DROP TABLE IF EXISTS candidate_password_reset_tokens")
    op.execute("DROP INDEX IF EXISTS uq_candidate_profiles_email_lower")
    op.execute("DROP INDEX IF EXISTS idx_candidate_email")
    op.execute("DROP INDEX IF EXISTS idx_candidate_profiles_verified")
    op.execute("ALTER TABLE candidate_profiles DROP CONSTRAINT IF EXISTS candidate_profiles_email_key")
    for column in LEGACY_COLUMNS:
        op.execute(f"ALTER TABLE candidate_profiles DROP COLUMN IF EXISTS {column}")


def downgrade() -> None:
    op.execute("""
        ALTER TABLE candidate_profiles
            ADD COLUMN IF NOT EXISTS email text, ADD COLUMN IF NOT EXISTS name text,
            ADD COLUMN IF NOT EXISTS password_hash text, ADD COLUMN IF NOT EXISTS google_id text,
            ADD COLUMN IF NOT EXISTS is_registered boolean, ADD COLUMN IF NOT EXISTS is_verified boolean,
            ADD COLUMN IF NOT EXISTS verified_at timestamptz, ADD COLUMN IF NOT EXISTS verification_token_hash text,
            ADD COLUMN IF NOT EXISTS verification_sent_at timestamptz
    """)
    op.execute("""
        UPDATE candidate_profiles c SET
            email = u.email, name = u.name, password_hash = u.password_hash, google_id = u.google_id,
            is_registered = u.is_registered, is_verified = u.is_verified, verified_at = u.verified_at,
            verification_token_hash = u.verification_token_hash, verification_sent_at = u.verification_sent_at
        FROM users u WHERE u.id = c.id
    """)
    op.execute("ALTER TABLE candidate_profiles ADD CONSTRAINT candidate_profiles_email_key UNIQUE (email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_email ON candidate_profiles (email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_profiles_verified ON candidate_profiles (is_verified)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_profiles_email_lower ON candidate_profiles (lower(email))")

    op.execute("""
        CREATE TABLE IF NOT EXISTS candidate_refresh_tokens (
            id uuid PRIMARY KEY,
            candidate_id uuid NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
            token_hash text NOT NULL,
            expires_at timestamptz NOT NULL,
            revoked boolean NOT NULL DEFAULT false,
            created_at timestamptz DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_refresh_tokens_candidate ON candidate_refresh_tokens (candidate_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_refresh_tokens_hash ON candidate_refresh_tokens (token_hash)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS candidate_password_reset_tokens (
            id uuid PRIMARY KEY,
            candidate_id uuid NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
            token_hash text NOT NULL,
            expires_at timestamptz NOT NULL,
            used boolean NOT NULL DEFAULT false,
            created_at timestamptz DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_reset_tokens_candidate ON candidate_password_reset_tokens (candidate_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_candidate_reset_tokens_hash ON candidate_password_reset_tokens (token_hash)")
    op.execute("""
        INSERT INTO candidate_refresh_tokens (id, candidate_id, token_hash, expires_at, revoked, created_at)
        SELECT r.id, r.user_id, r.token_hash, r.expires_at, r.revoked, r.created_at
        FROM refresh_tokens r WHERE r.actor = 'candidate' AND EXISTS (SELECT 1 FROM candidate_profiles c WHERE c.id = r.user_id)
        ON CONFLICT (id) DO NOTHING
    """)
    op.execute("""
        INSERT INTO candidate_password_reset_tokens (id, candidate_id, token_hash, expires_at, used, created_at)
        SELECT r.id, r.user_id, r.token_hash, r.expires_at, r.used, r.created_at
        FROM user_password_reset_tokens r WHERE EXISTS (SELECT 1 FROM candidate_profiles c WHERE c.id = r.user_id)
        ON CONFLICT (id) DO NOTHING
    """)
