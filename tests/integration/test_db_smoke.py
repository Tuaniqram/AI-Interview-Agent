"""Example integration test — self-skips without DATABASE_URL.

Replace the body with real DB-backed assertions (e.g. model CRUD round-trip,
resolver against seeded rows) when a test DB is available.
"""
import pytest

pytestmark = pytest.mark.integration


def test_database_is_reachable(live_db):
    import sqlalchemy

    engine = sqlalchemy.create_engine(live_db)
    with engine.connect() as conn:
        assert conn.execute(sqlalchemy.text("SELECT 1")).scalar() == 1
