"""Remove the data the e2e / smoke runs create.

Deliberately narrow: only users and candidates whose email matches the test patterns below
(``...@example.com``), the organizations those users own, and their CV files under ``resumes/``.
Real accounts never match.

    python tools/e2e/cleanup.py            # use DATABASE_URL from .env
    E2E_USE_POOLER=1 python tools/e2e/cleanup.py
"""
import asyncio
import os
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.chdir(REPO)

if os.environ.get("E2E_USE_POOLER") == "1":
    from dotenv import dotenv_values

    _url = dotenv_values(REPO / ".env")["DATABASE_URL"]
    _m = re.match(r"postgres(?:ql)?://([^:]+):(.+)@([^@:/]+):(\d+)/(\w+)$", _url)
    _u, _pwd, _host, _p, _db = _m.groups()
    if "pooler.supabase.com" not in _host:
        os.environ["DATABASE_URL"] = (
            f"postgresql://postgres.{_host.split('.')[1]}:{_pwd}@aws-0-ap-southeast-2.pooler.supabase.com:6543/{_db}"
        )

from sqlalchemy import text  # noqa: E402

from app.database.session import get_session_factory  # noqa: E402

PATTERN = r"^(e2e-|acct-smoke-|phase[0-9]+-smoke-).*@example\.com$"


async def main() -> None:
    factory = get_session_factory()
    if factory is None:
        print("DATABASE_URL is not configured; nothing to clean")
        return
    async with factory() as s:
        async def rows(sql, **params):
            return (await s.execute(text(sql), params)).all()

        cands = [r[0] for r in await rows("select id from candidate_profiles where email ~* :p", p=PATTERN)]
        users = [r[0] for r in await rows("select id from users where email ~* :p", p=PATTERN)]
        orgs = [r[0] for r in await rows("select id from organizations where owner_user_id = any(:u)", u=users)] if users else []
        print(f"candidates={len(cands)} users={len(users)} orgs={len(orgs)}")

        paths: list[str] = []
        if cands:
            docs = await rows("select document_metadata->>'path' from candidate_documents where candidate_id = any(:c)", c=cands)
            paths = [r[0] for r in docs if r[0]]
            await s.execute(text("delete from interview_sessions where candidate_profile_id = any(:c)"), {"c": cands})
            await s.execute(text("delete from public_interview_submissions where candidate_profile_id = any(:c)"), {"c": cands})
            for table in ("candidate_documents", "candidate_refresh_tokens", "candidate_password_reset_tokens", "candidate_saved_listings"):
                await s.execute(text(f"delete from {table} where candidate_id = any(:c)"), {"c": cands})
            await s.execute(text("delete from candidate_profiles where id = any(:c)"), {"c": cands})
        if orgs:
            await s.execute(text("delete from interview_sessions where org_id = any(:o)"), {"o": orgs})
            await s.execute(text("delete from public_interviews where org_id = any(:o)"), {"o": orgs})
            await s.execute(text("delete from audit_log where org_id = any(:o)"), {"o": orgs})
            await s.execute(text("delete from organizations where id = any(:o)"), {"o": orgs})
        if users:
            await s.execute(text("delete from audit_log where user_id = any(:u)"), {"u": users})
            for table in ("refresh_tokens", "user_password_reset_tokens"):
                await s.execute(text(f"delete from {table} where user_id = any(:u)"), {"u": users})
            await s.execute(text("delete from users where id = any(:u)"), {"u": users})
        await s.commit()

    resumes = (REPO / "resumes").resolve()
    removed = 0
    for p in paths:
        path = Path(p).resolve()
        if path.is_file() and resumes in path.parents:
            path.unlink()
            removed += 1
    print(f"resume files removed: {removed}")


if __name__ == "__main__":
    asyncio.run(main())
