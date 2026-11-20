"""Proves the final cleanup migration (b8e9f0a1b2c3) on the REAL data inside a transaction that is always rolled back:
upgrade, check the result, downgrade, and check the old identity and sessions are rebuilt exactly from `users` / `refresh_tokens`.

    venv/Scripts/python.exe scripts/unify_users_cleanup_dry_run.py
"""
import asyncio
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from alembic.migration import MigrationContext  # noqa: E402
from alembic.operations import Operations  # noqa: E402

from app.database.session import get_engine  # noqa: E402

FAILED: list[str] = []


def check(ok: bool, what: str, detail: str = "") -> None:
    print(("  [ok ] " if ok else "  [FAIL] ") + what + (f" - {detail}" if detail else ""))
    if not ok:
        FAILED.append(what)


def q1(c, sql):
    return c.exec_driver_sql(sql).scalar()


def load():
    path = os.path.join(ROOT, "alembic", "versions", "b8e9f0a1b2c3_unify_users_drop_legacy.py")
    spec = importlib.util.spec_from_file_location("cleanup_migration", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Rollback(Exception):
    pass


def body(c):
    mig = load()
    ctx = MigrationContext.configure(c)
    cols = lambda: sorted(r[0] for r in c.exec_driver_sql(
        "select column_name from information_schema.columns where table_schema='public' and table_name='candidate_profiles'").all())
    tables = lambda: sorted(r[0] for r in c.exec_driver_sql(
        "select table_name from information_schema.tables where table_schema='public' and table_name like 'candidate_%token%'").all())

    before_cols, before_tables = cols(), tables()
    ident = """select c.id, c.email, c.name, c.password_hash, c.google_id, c.is_registered, c.is_verified
               from candidate_profiles c order by c.id"""
    sessions = "select count(*) from candidate_refresh_tokens"
    users_before = q1(c, "select count(*) from users")
    profiles_before = q1(c, "select count(*) from candidate_profiles")
    print("before:", before_cols, before_tables)

    with Operations.context(ctx):
        mig.upgrade()
    print("after: ", cols(), tables())
    check(tables() == [], "both legacy token tables are gone")
    check(set(cols()) == {"id", "phone", "resume_url", "skills", "profile_data", "created_at", "updated_at"},
          "candidate_profiles keeps only candidate data")
    check(q1(c, "select count(*) from users") == users_before, "users untouched")
    check(q1(c, "select count(*) from candidate_profiles") == profiles_before, "no candidate profile lost")
    check(q1(c, "select count(*) from candidate_profiles p join users u on u.id = p.id") == profiles_before,
          "every profile still has its account")

    with Operations.context(ctx):
        mig.downgrade()
    check(cols() == before_cols and tables() == before_tables, "downgrade restores the same columns and tables")
    rows = c.exec_driver_sql(ident).all()
    mism = q1(c, """select count(*) from candidate_profiles c join users u on u.id = c.id
                    where c.email is distinct from u.email or c.name is distinct from u.name
                       or c.password_hash is distinct from u.password_hash or c.google_id is distinct from u.google_id
                       or c.is_registered is distinct from u.is_registered or c.is_verified is distinct from u.is_verified""")
    check(len(rows) == profiles_before and mism == 0, "downgrade rebuilds the old identity from users (current values)")
    check(q1(c, sessions) >= q1(c, "select count(*) from refresh_tokens where actor='candidate'"),
          "downgrade rebuilds the candidate sessions from refresh_tokens")


async def main() -> int:
    engine = get_engine()
    async with engine.connect() as conn:
        outer = await conn.begin()
        try:
            await conn.run_sync(lambda sc: body(sc))
        finally:
            await outer.rollback()
    print("\ntransaction ROLLED BACK (nothing was committed)")
    async with engine.connect() as conn:
        tables = (await conn.exec_driver_sql(
            "select count(*) from information_schema.tables where table_schema='public' and table_name in "
            "('candidate_refresh_tokens','candidate_password_reset_tokens')")).scalar()
    check(tables == 2, "the real database still has both legacy tables")
    await engine.dispose()
    print("\nRESULT:", "ALL CHECKS PASSED" if not FAILED else f"{len(FAILED)} CHECK(S) FAILED: " + "; ".join(FAILED))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
