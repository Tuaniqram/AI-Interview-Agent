"""The final report as a background job.

The last answer is scored as usual; the report (about 25-37 s of LLM reading) is then built by a job,
so the candidate hears "interview complete" at once and a dropped connection or a restart cannot lose
the report.

* Queue: the Redis stream ``aura:events:report_jobs``, one consumer group, a consumer inside every
  worker (no extra service). Redis commands are scarce on a hosted plan, so a consumer wakes when its
  own worker enqueues and otherwise sweeps once a minute for jobs nobody finished.
* A job that fails is retried (``MAX_ATTEMPTS``); a job whose worker died is claimed by another once
  its heartbeat stops.
* Running a job twice is safe: a finalized interview is never rebuilt, and the session's
  compare-and-set lets only one of two concurrent builds be stored.
* ``aura:events:{session_id}`` announces ``report_ready`` to whichever worker holds the socket.
* Without Redis nothing is queued and the report is built inline, as before.
"""
import asyncio
import logging
import os
import uuid

from app.services import llm_budget
from app.services.redis_client import AsyncLink

logger = logging.getLogger(__name__)

STREAM = "aura:events:report_jobs"
GROUP = "report-builders"
QUEUED_PREFIX = "aura:events:queued:"
CHANNEL_PREFIX = "aura:events:"
STREAM_TTL_S = 7 * 24 * 3600
QUEUED_TTL_S = 10 * 60
JOB_TIMEOUT_S = 240
HEARTBEAT_S = 20
CLAIM_AFTER_MS = 60_000  # no heartbeat for this long: the worker holding the job is gone
SWEEP_S = float(os.getenv("REPORT_SWEEP_S", "60"))
MAX_ATTEMPTS = 3
RETRY_DELAYS_S = (2, 10)
WATCH_TIMEOUT_S = 15 * 60
WATCH_CHECK_S = 10


def background_enabled() -> bool:
    return os.getenv("REPORT_BACKGROUND", "1").strip().lower() not in ("0", "false", "no")


async def build_report(session_id: str, store=None, v5_persister=None) -> None:
    """Build and save the report of a session that is waiting for it. Safe to call twice."""
    from app.engine.decision import finalize_session
    from app.engine.engine import InterviewEngine
    from app.engine.persistence import persist_v5_snapshot
    from app.engine.store_io import store_get
    from app.exceptions import StaleSessionError
    from app.core.interview_state import dict_to_brain
    from app.services.v4_session_store import get_v4_session_store

    store = store or get_v4_session_store()
    raw = await store_get(store, session_id)
    if raw is None:
        logger.warning("Report job: session %s no longer exists", session_id[:12])
        return
    brain = dict_to_brain(raw)
    if brain.finalized:
        # A previous run may have died between saving the state and the reporting snapshot.
        await persist_v5_snapshot(session_id, brain, v5_persister, finalize=True)
        return
    if not brain.report_pending:
        return
    engine = InterviewEngine(store=store, v5_persister=v5_persister)  # no queue: builds right here
    with llm_budget.scope(session_id, getattr(brain, "org_id", None)):
        try:
            await finalize_session(engine, brain)
        except StaleSessionError:
            logger.info("Report job: %s was finished by another run", session_id[:12])


class ReportQueue:
    def __init__(self, client=None, builder=build_report, block: bool = True):
        self._redis = AsyncLink("report jobs", client)
        self._builder = builder
        self.consumer = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self._wake: asyncio.Event | None = None
        self._task: asyncio.Task | None = None

    @property
    def active(self) -> bool:
        """A consumer is running in this process, so enqueued work will be done."""
        return self._task is not None and not self._task.done() and background_enabled()

    # -- producer ---------------------------------------------------------

    async def enqueue(self, session_id: str) -> bool:
        """True when a job for this session is queued (now or already); False without Redis."""
        client = self._redis.client()
        if client is None:
            return False
        try:
            if not await client.set(QUEUED_PREFIX + session_id, "1", nx=True, ex=QUEUED_TTL_S):
                return True
            try:
                await client.xadd(STREAM, {"session_id": session_id}, maxlen=10_000, approximate=True)
                await client.expire(STREAM, STREAM_TTL_S)
            except Exception:
                await client.delete(QUEUED_PREFIX + session_id)
                raise
        except Exception as exc:  # noqa: BLE001
            self._redis.failed(exc)
            return False
        if self._wake is not None:
            self._wake.set()
        return True

    # -- consumer ---------------------------------------------------------

    def start(self) -> None:
        if self._task is None and background_enabled() and self._redis.client() is not None:
            self._wake = asyncio.Event()
            self._task = asyncio.create_task(self._consume())

    async def stop(self) -> None:
        """Unfinished jobs stay in the stream and are claimed by another worker."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except BaseException:  # noqa: BLE001 - cancellation
                pass
            self._task = None

    async def _consume(self) -> None:
        while True:
            self._wake.clear()
            try:
                while await self.run_once():
                    pass
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - the consumer must outlive any single failure
                logger.exception("Report queue sweep failed")
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=SWEEP_S)
            except asyncio.TimeoutError:
                pass

    async def run_once(self, claim_after_ms: int = CLAIM_AFTER_MS) -> bool:
        """Take one job (an abandoned one first) and run it. False when there is nothing to do."""
        client = self._redis.client()
        if client is None:
            return False
        try:
            entry = await self._next_entry(client, claim_after_ms)
        except Exception as exc:  # noqa: BLE001
            if "NOGROUP" in str(exc):
                try:
                    await client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
                    await client.expire(STREAM, STREAM_TTL_S)
                    return True
                except Exception as create_exc:  # noqa: BLE001
                    exc = create_exc
                    if "BUSYGROUP" in str(create_exc):
                        return True
            self._redis.failed(exc)
            return False
        if entry is None:
            return False
        await self._run(client, *entry)
        return True

    async def _next_entry(self, client, claim_after_ms: int):
        claimed = await client.xautoclaim(STREAM, GROUP, self.consumer, min_idle_time=claim_after_ms,
                                          start_id="0-0", count=1)
        entries = claimed[1]
        if not entries:
            fresh = await client.xreadgroup(GROUP, self.consumer, {STREAM: ">"}, count=1)
            entries = fresh[0][1] if fresh else []
        if not entries:
            return None
        message_id, fields = entries[0]
        return message_id, (fields or {}).get("session_id")

    async def _run(self, client, message_id: str, session_id: str | None) -> None:
        pending = await client.xpending_range(STREAM, GROUP, min=message_id, max=message_id, count=1)
        deliveries = pending[0]["times_delivered"] if pending else 1
        if not session_id or deliveries > MAX_ATTEMPTS:
            logger.error("Report job for %s dropped after %d deliveries", str(session_id)[:12], deliveries)
            await self._finish(client, message_id, session_id, ready=False)
            return
        heartbeat = asyncio.create_task(self._heartbeat(client, message_id))
        try:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    await asyncio.wait_for(self._builder(session_id), timeout=JOB_TIMEOUT_S)
                    await self._finish(client, message_id, session_id, ready=True)
                    return
                except asyncio.CancelledError:
                    raise  # shutting down: leave the job for another worker
                except Exception:  # noqa: BLE001
                    logger.exception("Report job for %s failed (attempt %d/%d)",
                                     session_id[:12], attempt, MAX_ATTEMPTS)
                    if attempt < MAX_ATTEMPTS:
                        await asyncio.sleep(RETRY_DELAYS_S[min(attempt - 1, len(RETRY_DELAYS_S) - 1)])
            # Give up for now; the next visit of the candidate queues it again.
            await self._finish(client, message_id, session_id, ready=False)
        finally:
            heartbeat.cancel()

    async def _heartbeat(self, client, message_id: str) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_S)
            try:  # JUSTID resets the idle time without counting a delivery
                await client.xclaim(STREAM, GROUP, self.consumer, 0, [message_id], justid=True)
            except Exception as exc:  # noqa: BLE001
                self._redis.failed(exc)

    async def _finish(self, client, message_id: str, session_id: str | None, ready: bool) -> None:
        try:
            await client.xack(STREAM, GROUP, message_id)
            await client.xdel(STREAM, message_id)
            if session_id:
                await client.delete(QUEUED_PREFIX + session_id)
                if ready:
                    await client.publish(CHANNEL_PREFIX + session_id, "report_ready")
        except Exception as exc:  # noqa: BLE001 - at worst the job runs again and finds it done
            self._redis.failed(exc)

    # -- waiting for the result --------------------------------------------

    async def wait_for_report(self, session_id: str, store, timeout: float = WATCH_TIMEOUT_S,
                              check_every: float = WATCH_CHECK_S) -> dict | None:
        """The finished session state, or None after ``timeout``.

        Woken by the ``report_ready`` announcement; the state is also re-read now and then, so a
        missed message (or Redis going away) only delays the answer.
        """
        from app.engine.store_io import store_get

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        pubsub = None
        client = self._redis.client()
        if client is not None:
            try:
                pubsub = client.pubsub()
                await pubsub.subscribe(CHANNEL_PREFIX + session_id)  # before the first read: no gap
            except Exception as exc:  # noqa: BLE001
                self._redis.failed(exc)
                pubsub = None
        try:
            while loop.time() < deadline:
                state = await store_get(store, session_id)
                if state is not None and state.get("finalized"):
                    return state
                next_check = min(deadline, loop.time() + check_every)
                while loop.time() < next_check:
                    if pubsub is None:
                        await asyncio.sleep(max(0.0, next_check - loop.time()))
                        break
                    try:  # short waits: below the socket timeout, and no command is sent
                        if await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0):
                            break
                    except Exception as exc:  # noqa: BLE001
                        self._redis.failed(exc)
                        pubsub = None
            return None
        finally:
            if pubsub is not None:
                try:
                    await pubsub.aclose()
                except Exception:  # noqa: BLE001
                    pass


_queue: ReportQueue | None = None


def get_report_queue() -> ReportQueue:
    global _queue
    if _queue is None:
        async def builder(session_id: str) -> None:
            from app.services.v5_brain_persister import V5BrainPersister

            await build_report(session_id, v5_persister=V5BrainPersister())

        _queue = ReportQueue(builder=builder)
    return _queue


def active_queue_for(store) -> ReportQueue | None:
    """The queue to defer reports to, or None to build them inline.

    Only with the shared store: a job may run on any worker.
    """
    from app.services.v4_session_store import RedisV4SessionStore

    queue = get_report_queue()
    return queue if queue.active and isinstance(store, RedisV4SessionStore) else None
