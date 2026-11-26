"""/health says whether Redis is reachable, and stays 200 either way."""
import fakeredis
import pytest
from fakeredis import FakeAsyncRedis
from starlette.testclient import TestClient

from app.main import app
from app.services import redis_client


def health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    return response.json()


def test_not_configured():
    assert health()["redis"] == "not_configured"


@pytest.mark.parametrize("connected, expected", [(True, "ok"), (False, "unreachable")])
def test_reports_whether_redis_answers(monkeypatch, connected, expected):
    server = fakeredis.FakeServer()
    server.connected = connected
    monkeypatch.setattr(redis_client, "redis_url", lambda: "redis://example:6379")
    monkeypatch.setattr(redis_client, "_health_link",
                        redis_client.AsyncLink("t", FakeAsyncRedis(server=server)))
    body = health()
    assert body["redis"] == expected
    assert body["session_store"] in ("memory", "redis")
