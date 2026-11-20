"""unify accounts, step 1: identity columns on users (additive; the running app is unaffected)

Revision ID: d4a5b6c7e8f9
Revises: c1a2b3c4d5e6
Create Date: 2026-11-20

Plan: docs/UNIFIED_USER_ACCOUNTS_PLAN.md. Every column added here has a default that matches what the current code
writes, so the deployed backend keeps working unchanged after this runs.

* users gains the fields candidates used to keep on candidate_profiles (google_id, verification) and may have no
  password (an unclaimed guest).
* A registered account must have a way to sign in: password or Google (check constraint).
* Emails are unique case-insensitively, so "A@x.com" and "a@x.com" can never be two identities (production already
  had this index; it is created only if missing and never dropped by the downgrade).
* refresh_tokens gains `actor`: the kind of session a refresh token may mint ('org' or 'candidate'). A candidate's refresh
  token must never be exchangeable for a hiring-side access token once both kinds share this table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4a5b6c7e8f9"
down_revision: Union[str, None] = "c1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Refuse to build the case-insensitive unique index over data that already breaks it, with a readable message.
    dupes = op.get_bind().execute(
        sa.text("select count(*) from (select lower(email) from users group by 1 having count(*) > 1) d")
    ).scalar()
    if dupes:
        raise RuntimeError(f"{dupes} email(s) in users differ only by letter case; resolve them before this migration")

    op.add_column("users", sa.Column("google_id", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("is_registered", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("verification_token_hash", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("verification_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=True)

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_google_id ON public.users (google_id) WHERE google_id IS NOT NULL")
    # Production already has this exact index (added outside the migrations); IF NOT EXISTS makes a fresh database get it too.
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower ON public.users (lower(email))")
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT users_can_sign_in_check "
        "CHECK (is_registered = false OR password_hash IS NOT NULL OR google_id IS NOT NULL)"
    )

    op.add_column("refresh_tokens", sa.Column("actor", sa.Text(), nullable=False, server_default="org"))
    op.execute("ALTER TABLE refresh_tokens ADD CONSTRAINT refresh_tokens_actor_check CHECK (actor IN ('org', 'candidate'))")


def downgrade() -> None:
    op.execute("ALTER TABLE refresh_tokens DROP CONSTRAINT IF EXISTS refresh_tokens_actor_check")
    op.drop_column("refresh_tokens", "actor")

    # password_hash goes back to required, which is impossible while guest accounts without a password exist.
    guests = op.get_bind().execute(sa.text("select count(*) from users where password_hash is null")).scalar()
    if guests:
        raise RuntimeError(f"{guests} user(s) have no password (unclaimed guests or Google sign-ups); cannot restore NOT NULL")

    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_can_sign_in_check")
    # uq_users_email_lower is deliberately NOT dropped: it existed in production before this migration and is a security
    # control (no two accounts whose emails differ only by letter case), so removing it would weaken the database.
    op.execute("DROP INDEX IF EXISTS public.uq_users_google_id")
    op.alter_column("users", "password_hash", existing_type=sa.Text(), nullable=False)
    for column in ("verification_sent_at", "verification_token_hash", "verified_at", "is_verified", "is_registered", "google_id"):
        op.drop_column("users", column)
