"""The unit suite must never reach the services configured in a developer's `.env`."""
import os


def test_redis_from_dotenv_is_not_visible_to_tests():
    from app.services.redis_client import redis_url  # loads .env, as the app does

    assert os.environ.get("REDIS_URL") == ""
    assert redis_url() == ""
    assert os.environ.get("SESSION_STORE_BACKEND") == "memory"
