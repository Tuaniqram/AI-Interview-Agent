from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "docs" / "it-scope" / "seed-it-catalog.sql"


def main() -> int:
    load_dotenv(ROOT / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 1

    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    sql = SEED_PATH.read_text(encoding="utf-8")

    with psycopg2.connect(database_url, connect_timeout=15) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            cursor.execute("SELECT count(*) FROM it_roles")
            role_count = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM competencies")
            competency_count = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM role_competencies")
            mapping_count = cursor.fetchone()[0]
        connection.commit()

    print(f"seeded roles={role_count} competencies={competency_count} mappings={mapping_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
