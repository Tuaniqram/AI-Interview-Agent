"""Export the tables the unify-accounts migrations read or copy, before anything touches production.

    python scripts/unify_users_backup.py

Writes backups/unify-users-<UTC timestamp>.json (the folder is git-ignored). READ-ONLY: it only runs SELECTs.

The file contains password hashes and token hashes, so treat it like .env: keep it private, do not commit, upload or share it,
and delete it once the unify work is finished and verified. It prints row counts only, never values.
"""
import asyncio
import datetime as dt
import json
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import text  # noqa: E402

load_dotenv(ROOT / ".env")
from app.database.session import get_engine  # noqa: E402

TABLES = [
    "users", "candidate_profiles", "refresh_tokens", "candidate_refresh_tokens",
    "user_password_reset_tokens", "candidate_password_reset_tokens", "organizations",
]


def encode(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    raise TypeError(type(value))


async def main() -> None:
    engine = get_engine()
    out: dict = {"taken_at": dt.datetime.now(dt.timezone.utc).isoformat(), "tables": {}}
    async with engine.connect() as conn:
        out["alembic_version"] = (await conn.execute(text("select version_num from alembic_version"))).scalar()
        for table in TABLES:  # names come from the list above, never from input
            rows = (await conn.execute(text(f"select * from public.{table}"))).mappings().all()
            out["tables"][table] = [dict(r) for r in rows]
            print("%-34s %3d rows" % (table, len(rows)))
    await engine.dispose()
    folder = ROOT / "backups"
    folder.mkdir(exist_ok=True)
    path = folder / ("unify-users-%s.json" % dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    path.write_text(json.dumps(out, default=encode, indent=1), encoding="utf-8")
    print("\nwrote %s (%.1f KB). Private: contains hashes. Not committed (backups/ is ignored)." % (path, path.stat().st_size / 1024))


if __name__ == "__main__":
    asyncio.run(main())
