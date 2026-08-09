"""Integration-test scaffolding.

Tests in this directory require live services (Postgres via DATABASE_URL,
optionally a running API server / LLM provider). They are marked ``integration``
and are EXCLUDED from the default ``pytest`` run. Nothing here may run without
an explicit ``-m integration`` flag, and each test must self-skip cleanly when
its required service is absent.
"""
import os

import pytest


def database_url() -> str | None:
    return os.getenv("DATABASE_URL") or os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def live_db():
    """Skip the test unless a real Postgres DATABASE_URL is provided."""
    url = database_url()
    if not url:
        pytest.skip("DATABASE_URL not set — integration DB tests skipped")
    return url
