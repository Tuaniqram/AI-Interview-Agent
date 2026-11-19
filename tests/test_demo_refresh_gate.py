"""The anonymous demo wipe route is closed unless DEMO_TOOLS_ENABLED is set and the app URL is local."""
import pytest
from fastapi import HTTPException

from app.api.v1 import demo


class _Result:
    rowcount = 3


class _DB:
    def __init__(self):
        self.statements = []
        self.commits = 0

    async def execute(self, statement):
        self.statements.append(str(statement))
        return _Result()

    async def commit(self):
        self.commits += 1


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setattr(demo.settings, "DEMO_TOOLS_ENABLED", False)
    monkeypatch.setattr(demo.settings, "APP_URL", "http://localhost:5173")
    return demo.settings


async def test_default_configuration_refuses_even_with_a_localhost_app_url(settings):
    """The case behind the finding: APP_URL left at its localhost default must not open the route."""
    db = _DB()
    with pytest.raises(HTTPException) as exc:
        await demo.refresh_demo_db(db)
    assert exc.value.status_code == 403
    assert db.statements == [] and db.commits == 0


async def test_enabled_but_deployed_url_still_refuses(settings, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_TOOLS_ENABLED", True)
    monkeypatch.setattr(settings, "APP_URL", "https://interviews.example.com")
    db = _DB()
    with pytest.raises(HTTPException) as exc:
        await demo.refresh_demo_db(db)
    assert exc.value.status_code == 403
    assert db.statements == []


async def test_enabled_on_localhost_runs(settings, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_TOOLS_ENABLED", True)
    db = _DB()
    result = await demo.refresh_demo_db(db)
    assert result["deleted"] == {"interview_sessions": 3}
    assert db.commits == 1
