"""Dry run of the unify-accounts migrations against the real database. NOTHING IS EVER COMMITTED.

    python scripts/unify_users_dry_run.py

Opens a transaction, applies the two migrations (d4a5b6c7e8f9, e5b6c7d8f9a0), checks the result on the real rows, applies them a
second time (they must be idempotent), runs the downgrades and checks the database is back to how it started, then ROLLS BACK
and checks again from a fresh connection that the database really is untouched. Prints counts only, never emails or hashes.
Exit code 0 = every check passed.
"""
import asyncio
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from alembic.operations import Operations  # noqa: E402
from alembic.runtime.migration import MigrationContext  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import text  # noqa: E402
from app.database.session import get_engine  # noqa: E402  (the app's engine: pooler-safe, no prepared-statement cache)

load_dotenv(ROOT / ".env")

FAILED: list[str] = []


def check(ok: bool, what: str, detail: str = "") -> None:
    print("  [%s] %s%s" % ("ok " if ok else "FAIL", what, (" - " + detail) if detail else ""))
    if not ok:
        FAILED.append(what)


def load(name: str):
    path = next((ROOT / "alembic" / "versions").glob(name + "_*.py"))
    spec = importlib.util.spec_from_file_location("mig_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def q1(c, sql: str):
    return c.execute(text(sql)).scalar()


def snapshot(c) -> dict:
    return {
        "users": q1(c, "select count(*) from users"),
        "candidates": q1(c, "select count(*) from candidate_profiles"),
        "refresh": q1(c, "select count(*) from refresh_tokens"),
        "cand_refresh": q1(c, "select count(*) from candidate_refresh_tokens"),
        "reset": q1(c, "select count(*) from user_password_reset_tokens"),
        "cand_reset": q1(c, "select count(*) from candidate_password_reset_tokens"),
        "new_user_columns": q1(c, "select count(*) from information_schema.columns where table_schema='public' and table_name='users' and column_name in "
                                  "('google_id','is_registered','is_verified','verified_at','verification_token_hash','verification_sent_at')"),
        "actor_column": q1(c, "select count(*) from information_schema.columns where table_schema='public' and table_name='refresh_tokens' and column_name='actor'"),
        "log_table": q1(c, "select count(*) from information_schema.tables where table_schema='public' and table_name='unify_users_migration_log'"),
        "email_index": q1(c, "select count(*) from pg_indexes where schemaname='public' and indexname='uq_users_email_lower'"),
        "password_nullable": q1(c, "select is_nullable from information_schema.columns where table_schema='public' and table_name='users' and column_name='password_hash'"),
    }


def run_in_transaction(sync_conn):
    mig_a, mig_b = load("d4a5b6c7e8f9"), load("e5b6c7d8f9a0")
    before = snapshot(sync_conn)
    print("before:", before)
    ctx = MigrationContext.configure(sync_conn)

    with Operations.context(ctx):
        print("\napply step 1 (identity columns) and step 2 (copy candidates):")
        mig_a.upgrade()
        mig_b.upgrade()
    after = snapshot(sync_conn)
    print("after: ", after)

    check(after["users"] == before["users"] + before["candidates"], "every candidate became one users row",
          "%d -> %d" % (before["users"], after["users"]))
    check(after["refresh"] == before["refresh"] + before["cand_refresh"], "candidate refresh tokens copied",
          "%d -> %d" % (before["refresh"], after["refresh"]))
    check(after["reset"] == before["reset"] + before["cand_reset"], "candidate reset tokens copied")
    check(after["candidates"] == before["candidates"] and after["cand_refresh"] == before["cand_refresh"]
          and after["cand_reset"] == before["cand_reset"], "old candidate tables untouched (copy, not move)")
    check(after["password_nullable"] == "YES", "users.password_hash can be empty (unclaimed guests)")

    mism = q1(sync_conn, """select count(*) from candidate_profiles c join users u on u.id = c.id
                            where u.email <> c.email or u.name <> c.name or u.password_hash is distinct from c.password_hash
                               or u.is_verified <> c.is_verified or u.is_registered <> c.is_registered
                               or u.google_id is distinct from c.google_id""")
    check(mism == 0, "copied identity (email, name, password hash, verification, google) matches exactly")
    check(q1(sync_conn, "select count(*) from candidate_profiles c where not exists (select 1 from users u where u.id = c.id)") == 0,
          "every candidate profile has a users row with the SAME id")
    check(q1(sync_conn, "select count(*) from users u join candidate_profiles c on c.id = u.id where u.is_admin") == 0,
          "no candidate was made an admin")
    check(q1(sync_conn, "select count(*) from refresh_tokens where actor = 'candidate'") == before["cand_refresh"],
          "copied candidate tokens are marked actor='candidate'")
    check(q1(sync_conn, "select count(*) from refresh_tokens where actor = 'org'") == before["refresh"],
          "existing hiring-side tokens are marked actor='org'")
    check(q1(sync_conn, "select count(*) from refresh_tokens r where not exists (select 1 from users u where u.id = r.user_id)") == 0,
          "no refresh token points at a missing user")
    check(q1(sync_conn, "select count(*) from users where is_admin") == q1(sync_conn, "select count(*) from users where is_admin and id not in (select candidate_id from unify_users_migration_log)"),
          "admin flags of existing users unchanged")

    # The constraints must reject for THEIR reason: every required column is supplied, and the error must name the constraint.
    rejects(sync_conn, "a registered account with no way to sign in is rejected", "users_can_sign_in_check",
            "insert into users (id, email, name, is_admin, is_active, is_registered) "
            "values (gen_random_uuid(), 'nobody@invalid.test', 'x', false, true, true)")
    rejects(sync_conn, "an email that differs only by letter case is rejected", "uq_users_email_lower",
            "insert into users (id, email, name, password_hash, is_admin, is_active) "
            "select gen_random_uuid(), upper(email), 'dup', 'x', false, true from users where email <> upper(email) limit 1")
    rejects(sync_conn, "an unknown token actor is rejected", "refresh_tokens_actor_check",
            "insert into refresh_tokens (id, user_id, token_hash, expires_at, revoked, actor) "
            "select gen_random_uuid(), id, 'h', now(), false, 'root' from users limit 1")
    rejects(sync_conn, "two accounts cannot share a Google id", "uq_users_google_id",
            "insert into users (id, email, name, is_admin, is_active, google_id) "
            "values (gen_random_uuid(), 'g1@invalid.test', 'g', false, true, 'same-google-id'), "
            "       (gen_random_uuid(), 'g2@invalid.test', 'g', false, true, 'same-google-id')")
    accepts(sync_conn, "an unclaimed guest (no password, not registered) is allowed",
            "insert into users (id, email, name, is_admin, is_active, is_registered) "
            "values (gen_random_uuid(), 'guest@invalid.test', 'g', false, true, false)")
    accepts(sync_conn, "a Google-only account (no password) is allowed",
            "insert into users (id, email, name, is_admin, is_active, is_registered, google_id) "
            "values (gen_random_uuid(), 'google@invalid.test', 'g', false, true, true, 'a-google-id')")

    with Operations.context(ctx):
        print("\nrun step 2 again (must change nothing):")
        mig_b.upgrade()
    again = snapshot(sync_conn)
    check(again == after, "step 2 is idempotent")

    with Operations.context(ctx):
        print("\nundo: downgrade step 2, then step 1:")
        mig_b.downgrade()
        mig_a.downgrade()
    restored = snapshot(sync_conn)
    print("restored:", restored)
    check(restored == before, "after the downgrades the database is exactly as it started")


class _Rollback(Exception):
    """Raised on purpose inside a savepoint so whatever the test inserted is undone."""


def rejects(sync_conn, what: str, constraint: str, sql: str) -> None:
    """The statement must fail, and the failure must be the named constraint (not some other missing column)."""
    try:
        with sync_conn.begin_nested():
            sync_conn.execute(text(sql))
    except Exception as exc:  # noqa: BLE001
        check(constraint in str(exc), what, "" if constraint in str(exc) else "rejected for another reason: " + str(exc)[:120])
        return
    check(False, what, "the statement was accepted")


def accepts(sync_conn, what: str, sql: str) -> None:
    """The statement must succeed; it is rolled back straight away."""
    try:
        with sync_conn.begin_nested():
            sync_conn.execute(text(sql))
            raise _Rollback()
    except _Rollback:
        check(True, what)
    except Exception as exc:  # noqa: BLE001
        check(False, what, str(exc)[:140])


async def main() -> int:
    engine = get_engine()
    async with engine.connect() as conn:
        trans = await conn.begin()
        await conn.run_sync(run_in_transaction)
        await trans.rollback()
        print("\ntransaction ROLLED BACK (nothing was committed)")
    async with engine.connect() as fresh:
        final = await fresh.run_sync(snapshot)
    print("fresh connection sees:", final)
    check(final["new_user_columns"] == 0 and final["actor_column"] == 0 and final["log_table"] == 0,
          "the real database has none of the new columns or tables")
    check(final["email_index"] == 1, "the existing case-insensitive email index is still there")
    await engine.dispose()
    print("\nRESULT:", "ALL CHECKS PASSED" if not FAILED else "%d CHECK(S) FAILED: %s" % (len(FAILED), "; ".join(FAILED)))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
