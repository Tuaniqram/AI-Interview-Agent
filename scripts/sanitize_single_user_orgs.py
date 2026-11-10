"""Reduce every organization to its single owner account.

Members were removed from the product, so this script:
  1. drops the legacy ``org_users`` / ``org_invitations`` tables if they still exist;
  2. deletes non-admin accounts that own no organization and are not candidates;
  3. verifies every organization has exactly one active owner.

Safe to run more than once.

Usage:
    venv/Scripts/python.exe scripts/sanitize_single_user_orgs.py --dry-run
    venv/Scripts/python.exe scripts/sanitize_single_user_orgs.py
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session_factory

LEGACY_TABLES = ("org_users", "org_invitations")

ORPHAN_SQL = """
SELECT u.email
FROM users u
WHERE u.is_admin = false
  AND NOT EXISTS (SELECT 1 FROM organizations o WHERE o.owner_user_id = u.id)
  AND NOT EXISTS (SELECT 1 FROM candidate_profiles cp WHERE lower(cp.email) = lower(u.email))
  AND NOT EXISTS (SELECT 1 FROM candidate_invitations ci WHERE ci.created_by = u.id)
ORDER BY u.email
"""

DELETE_ORPHANS_SQL = """
DELETE FROM users u
WHERE u.is_admin = false
  AND NOT EXISTS (SELECT 1 FROM organizations o WHERE o.owner_user_id = u.id)
  AND NOT EXISTS (SELECT 1 FROM candidate_profiles cp WHERE lower(cp.email) = lower(u.email))
  AND NOT EXISTS (SELECT 1 FROM candidate_invitations ci WHERE ci.created_by = u.id)
RETURNING u.email
"""


async def _table_exists(db: AsyncSession, name: str) -> bool:
    return bool(await db.scalar(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = :name"
    ), {"name": name}))


async def sanitize(dry_run: bool) -> int:
    factory = get_session_factory()
    async with factory() as db:
        for table in LEGACY_TABLES:
            if not await _table_exists(db, table):
                continue
            if dry_run:
                print(f"[dry-run] would drop legacy table {table}")
            else:
                await db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"dropped legacy table {table}")

        orphans = [row[0] for row in (await db.execute(text(ORPHAN_SQL))).all()]
        print(f"accounts without an owned organization or candidate profile: {len(orphans)}")
        for email in orphans:
            print(f"  - {email}")

        if dry_run:
            print("dry run: no rows changed")
        elif orphans:
            deleted = [row[0] for row in (await db.execute(text(DELETE_ORPHANS_SQL))).all()]
            await db.commit()
            print(f"deleted {len(deleted)} account(s)")
        else:
            print("nothing to delete")

        orgs = (await db.execute(text("""
            SELECT o.name, u.email, u.is_active
            FROM organizations o
            LEFT JOIN users u ON u.id = o.owner_user_id
            ORDER BY o.name
        """))).all()

        problems = []
        for name, email, is_active in orgs:
            if not email:
                problems.append(f"{name}: no owner")
            elif not is_active:
                problems.append(f"{name}: owner {email} is inactive")
        remaining = [row[0] for row in (await db.execute(text(ORPHAN_SQL))).all()]

        print(f"organizations checked: {len(orgs)}")
        for problem in problems:
            print(f"  ! {problem}")
        print(f"remaining accounts without an organization or candidate profile: {len(remaining)}")
        for email in remaining:
            print(f"  - {email}")

        if problems:
            return 1
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report changes without applying them")
    args = parser.parse_args()
    return asyncio.run(sanitize(args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
