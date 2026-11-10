"""Clear the database and run seed_v2.

Catalog tables (it_roles, competencies, role_competencies) are preserved so the
IT role catalog does not need re-seeding. The alembic version is never touched.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.database.session import get_session_factory

KEEP_TABLES = {"alembic_version", "it_roles", "competencies", "role_competencies"}


async def reset():
    factory = get_session_factory()
    async with factory() as session:
        rows = (await session.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        ))).all()
        tables = [row[0] for row in rows if row[0] not in KEEP_TABLES]
        if tables:
            quoted = ", ".join(f'"{name}"' for name in tables)
            await session.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
        await session.commit()
    print(f"Cleared {len(tables)} table(s); catalog tables preserved.")


if __name__ == "__main__":
    asyncio.run(reset())
    print("\nRunning seed...\n")
    from seed_v2 import seed

    asyncio.run(seed())
