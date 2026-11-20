"""unify accounts, step 3a: the old identity columns on candidate_profiles become optional

Revision ID: f6c7d8e9a0b1
Revises: e5b6c7d8f9a0
Create Date: 2026-11-20

Plan: docs/UNIFIED_USER_ACCOUNTS_PLAN.md. Apply this BEFORE the new code is deployed. The new code keeps identity on `users` and
creates candidate_profiles rows without email, name, is_registered or is_verified, which these four columns would reject while
they are NOT NULL. The previous code still fills them, so it keeps working after this migration.

The downgrade is the rollback path to the previous code. Before restoring NOT NULL it copies the CURRENT identity and sessions
from `users` / `refresh_tokens` back into the legacy columns and token tables, so a rollback does not resurrect an old
password or drop signed-in candidates:
  * candidate_profiles <- email, name, password hash, Google id, verification fields from users (same id)
  * candidate_refresh_tokens / candidate_password_reset_tokens <- tokens issued after the cutover, plus their revoked/used flags
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6c7d8e9a0b1"
down_revision: Union[str, None] = "e5b6c7d8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ("email", "name", "is_registered", "is_verified")


def upgrade() -> None:
    for column in COLUMNS:
        op.execute(f"ALTER TABLE candidate_profiles ALTER COLUMN {column} DROP NOT NULL")


def downgrade() -> None:
    conn = op.get_bind()

    orphans = conn.execute(sa.text(
        "select count(*) from candidate_profiles c where not exists (select 1 from users u where u.id = c.id)"
    )).scalar()
    if orphans:
        raise RuntimeError(f"{orphans} candidate profile(s) have no users row; cannot copy their identity back")

    op.execute("""
        UPDATE candidate_profiles c SET
            email = u.email, name = u.name, password_hash = u.password_hash, google_id = u.google_id,
            is_registered = u.is_registered, is_verified = u.is_verified, verified_at = u.verified_at,
            verification_token_hash = u.verification_token_hash, verification_sent_at = u.verification_sent_at
        FROM users u WHERE u.id = c.id
    """)

    # Sessions issued after the cutover, and the state of the ones that already existed.
    op.execute("""
        INSERT INTO candidate_refresh_tokens (id, candidate_id, token_hash, expires_at, revoked, created_at)
        SELECT r.id, r.user_id, r.token_hash, r.expires_at, r.revoked, r.created_at
        FROM refresh_tokens r
        WHERE r.actor = 'candidate'
          AND EXISTS (SELECT 1 FROM candidate_profiles c WHERE c.id = r.user_id)
          AND NOT EXISTS (SELECT 1 FROM candidate_refresh_tokens t WHERE t.id = r.id)
    """)
    op.execute("""
        UPDATE candidate_refresh_tokens t SET revoked = r.revoked
        FROM refresh_tokens r WHERE r.id = t.id AND r.actor = 'candidate'
    """)
    op.execute("""
        INSERT INTO candidate_password_reset_tokens (id, candidate_id, token_hash, expires_at, used, created_at)
        SELECT r.id, r.user_id, r.token_hash, r.expires_at, r.used, r.created_at
        FROM user_password_reset_tokens r
        WHERE EXISTS (SELECT 1 FROM candidate_profiles c WHERE c.id = r.user_id)
          AND NOT EXISTS (SELECT 1 FROM candidate_password_reset_tokens t WHERE t.id = r.id)
    """)
    op.execute("""
        UPDATE candidate_password_reset_tokens t SET used = r.used
        FROM user_password_reset_tokens r WHERE r.id = t.id
    """)

    for column in COLUMNS:
        op.execute(f"ALTER TABLE candidate_profiles ALTER COLUMN {column} SET NOT NULL")
