"""Background job that deletes long-expired refresh tokens (see ``accounts.purge_expired_refresh_tokens``)."""
import asyncio
import logging

logger = logging.getLogger(__name__)

STARTUP_DELAY_S = 120  # let the server and its database pool come up first
INTERVAL_S = 24 * 60 * 60


async def purge_once() -> int:
    """One purge pass in its own session. Never raises; returns the rows deleted (0 on any failure)."""
    try:
        from app.auth.accounts import purge_expired_refresh_tokens
        from app.database.session import get_session_factory

        factory = get_session_factory()
        if factory is None:
            return 0
        async with factory() as db:
            deleted = await purge_expired_refresh_tokens(db)
        if deleted:
            logger.info(f"Deleted {deleted} expired refresh token(s)")
        return deleted
    except Exception as exc:  # noqa: BLE001 - housekeeping must never affect the app
        logger.warning(f"Refresh token cleanup failed (non-fatal): {exc}")
        return 0


async def cleanup_loop(startup_delay: float = STARTUP_DELAY_S, interval: float = INTERVAL_S) -> None:
    await asyncio.sleep(startup_delay)
    while True:
        await purge_once()
        await asyncio.sleep(interval)
