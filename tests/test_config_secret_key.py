"""A deployed instance must not run with the public development SECRET_KEY."""
import pytest
from pydantic import ValidationError

from app.config import DEV_SECRET_KEY, Settings


def _settings(**kw):
    # _env_file=None and explicit values: neither the developer's .env nor the shell can change the outcome.
    return Settings(_env_file=None, **kw)


def test_dev_key_with_a_deployed_url_refuses_to_start():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _settings(SECRET_KEY=DEV_SECRET_KEY, APP_URL="https://interviews.example.com")


def test_dev_key_is_fine_for_a_local_run():
    assert _settings(SECRET_KEY=DEV_SECRET_KEY, APP_URL="http://localhost:5173").SECRET_KEY == DEV_SECRET_KEY
    assert _settings(SECRET_KEY=DEV_SECRET_KEY, APP_URL="http://127.0.0.1:8000").SECRET_KEY == DEV_SECRET_KEY


def test_own_key_is_fine_when_deployed():
    s = _settings(SECRET_KEY="a-long-random-value-from-a-secret-store", APP_URL="https://interviews.example.com")
    assert s.SECRET_KEY != DEV_SECRET_KEY


def test_empty_key_is_still_rejected():
    with pytest.raises(ValidationError):
        _settings(SECRET_KEY="", APP_URL="http://localhost:5173")
