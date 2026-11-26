"""The unit suite must never reach the services configured in a developer's `.env`."""
import os


def test_redis_from_dotenv_is_not_visible_to_tests():
    import app.services.cache as cache  # loads .env, as the app does

    assert os.environ.get("REDIS_URL") == ""
    assert cache.REDIS_URL == ""
    assert os.environ.get("SESSION_STORE_BACKEND") == "memory"
