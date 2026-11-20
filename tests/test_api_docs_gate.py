"""The interactive API docs (Swagger, ReDoc, openapi.json) are off on a deployed instance and on locally."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import docs_urls


def settings(**kw):
    # explicit values and no .env file: neither a developer's file nor the shell can change the outcome
    return Settings(_env_file=None, SECRET_KEY="a-long-random-value-from-a-secret-store", **kw)


@pytest.mark.parametrize("app_url,expected", [
    ("http://localhost:5173", True),
    ("http://127.0.0.1:3000", True),
    ("https://ai-interview-agent-drab-ten.vercel.app", False),
    ("https://interviews.example.com", False),
])
def test_unset_means_on_locally_and_off_when_deployed(app_url, expected):
    assert settings(APP_URL=app_url).api_docs_enabled is expected


@pytest.mark.parametrize("app_url", ["http://localhost:5173", "https://interviews.example.com"])
def test_an_explicit_value_always_wins(app_url):
    assert settings(APP_URL=app_url, ENABLE_API_DOCS=True).api_docs_enabled is True
    assert settings(APP_URL=app_url, ENABLE_API_DOCS=False).api_docs_enabled is False


def _app(enabled: bool) -> TestClient:
    app = FastAPI(**docs_urls(enabled))

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def test_when_off_none_of_the_three_urls_exist_but_the_api_still_works():
    client = _app(False)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path
    assert client.get("/api/ping").json() == {"ok": True}


def test_when_on_all_three_urls_are_served():
    client = _app(True)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 200, path


def test_the_real_app_keeps_its_schema_available_in_process():
    """Tests (and tools) read the schema with app.openapi(); turning the public URLs off must not break that."""
    from app.main import app

    assert len(app.openapi()["paths"]) > 50
