"""Acceptance run for the multi-worker backend: real uvicorn --workers 2, real Redis, real database.

    python tools/redis_acceptance/run.py                    # Redis up for the whole interview
    python tools/redis_acceptance/run.py --outage-after 3   # cut Redis after the third answer
    python tools/redis_acceptance/run.py --servers 2        # two server processes, connections alternate

``--servers`` matters on Windows, where ``--workers 2`` can hand every connection to the same worker.

One interview is driven over the WebSocket. The socket is dropped and reopened on every turn (once in
the middle of a turn) and one answer is sent twice at the same time. It checks that the question
number never goes back and that every answer was processed exactly once.

The server reaches Redis through a local TCP proxy, so "stopping Redis" is closing the proxy (a hosted
Redis cannot be stopped). Needs ``.env`` with DATABASE_URL, REDIS_URL and an LLM key. It writes one
practice session to the database and deletes it afterwards, and costs one short real interview.
"""
import argparse
import asyncio
import json
import os
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import dotenv_values  # noqa: E402

ENV = {k: (v or "").strip().strip('"') for k, v in dotenv_values(ROOT / ".env").items()}
os.environ["REDIS_URL"] = ""  # this script talks to the database only; the server gets the proxy

ANSWERS = [
    "I built the payments service in Python with FastAPI and PostgreSQL. I owned the idempotency layer: every request carries a key stored with a unique constraint, so a retried charge returns the first result.",
    "For retries I used a queue with exponential backoff and jitter, capped at five attempts, then a dead-letter table that an on-call engineer reviews. I added metrics on queue age and alerted past two minutes.",
    "The slow report endpoint did a sequential scan. EXPLAIN ANALYZE showed it, so I added a composite index on tenant and created date, and paginated by key instead of offset. It went from seconds to under 100 ms.",
    "We split reads to a replica. Because of replication lag I sent read-after-write requests to the primary for a few seconds per user, and kept money-related reads on the primary always.",
    "I cache the product catalog in Redis with a short TTL and delete the key on write. To avoid a stampede one request takes a lock and refreshes while the others serve the old value.",
    "For a schema change on a large table I add the column as nullable, backfill in batches, deploy code that writes both, then add the constraint as not valid and validate it afterwards.",
    "In an incident where connections ran out, I found a code path that held a transaction open during an HTTP call. I moved the call outside the transaction and added a statement timeout.",
    "I test with unit tests for the rules, integration tests against a real database in containers, and one end-to-end test for the payment path. Flaky tests get fixed or removed the same week.",
    "For service-to-service auth we used short-lived signed tokens with an audience claim, rotated keys through a key set endpoint, and logged every rejected token with the reason but never the token.",
    "I disagreed with a teammate about adding Kafka. I wrote down the load we actually had, showed a database queue handled it with room to spare, and we agreed on the numbers that would change our minds.",
]


class RedisProxy:
    """127.0.0.1 -> the hosted Redis (TLS if its URL says so). ``cut()`` is the outage."""

    def __init__(self, url: str):
        self.target = urlparse(url)
        self.server = None
        self.writers: set = set()
        self.port = 0

    async def start(self):
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        user = quote(unquote(self.target.username or "default"), safe="")
        password = quote(unquote(self.target.password or ""), safe="")
        return f"redis://{user}:{password}@127.0.0.1:{self.port}/0"

    async def _handle(self, reader, writer):
        context = ssl.create_default_context() if self.target.scheme == "rediss" else None
        try:
            up_reader, up_writer = await asyncio.open_connection(
                self.target.hostname, self.target.port or 6379, ssl=context,
                server_hostname=self.target.hostname if context else None)
        except OSError:
            writer.close()
            return
        self.writers |= {writer, up_writer}

        async def pipe(src, dst):
            try:
                while data := await src.read(65536):
                    dst.write(data)
                    await dst.drain()
            except (OSError, ssl.SSLError):
                pass
            finally:
                dst.close()

        await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer))

    def cut(self):
        self.server.close()
        for writer in self.writers:
            writer.transport.abort()
        self.writers.clear()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def worker_pid(server_port: int, client_port: int) -> int | None:
    """Which server process holds this connection (Windows ``netstat``; None elsewhere)."""
    if os.name != "nt":
        return None
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1] == f"127.0.0.1:{server_port}" and parts[2] == f"127.0.0.1:{client_port}":
            return int(parts[4])
    return None


class Client:
    def __init__(self, ports: list, sid: str, token: str, pids: list):
        # Connections are dealt to the servers in turn.
        self.port = ports[len(pids) % len(ports)]
        self.url = f"ws://127.0.0.1:{self.port}/ws/interview/{sid}?access={token}"
        self.pids, self.ws, self.counter = pids, None, 0

    async def connect(self):
        import websockets

        self.ws = await websockets.connect(self.url, max_size=None, ping_interval=None, open_timeout=30)
        await self.next()  # "connected"
        pid = worker_pid(self.port, self.ws.local_address[1])
        self.pids.append(pid)
        return self

    async def close(self):
        if self.ws is not None:
            await self.ws.close()
            self.ws = None

    async def next(self, timeout: float = 300):
        return json.loads(await asyncio.wait_for(self.ws.recv(), timeout))

    async def send(self, type_: str, **data):
        self.counter += 1
        await self.ws.send(json.dumps({"_id": str(self.counter), "type": type_, **data}))

    async def reply(self):
        """The answer to the last request (progress pushes skipped)."""
        while True:
            message = await self.next()
            if message.get("type") != "status":
                return message


async def database(action: str, sid: str):
    from sqlalchemy import text

    from app.database.session import get_session_factory
    from app.models.db import InterviewSession

    async with get_session_factory()() as db:
        if action == "create":
            role = (await db.execute(text(
                "select id, name from it_roles where slug='backend-developer' and is_active"))).one()
            db.add(InterviewSession(
                id=uuid.UUID(sid), it_role_id=role.id, job_role_snapshot=role.name, session_type="practice",
                interaction_mode="typing", total_questions=8, engine_version="v5"))
            await db.commit()
        elif action == "read":
            state = (await db.execute(text(
                "select cast(state as text) from v4_session_state where session_id=:s"), {"s": sid})).scalar()
            rows = (await db.execute(text(
                "select count(*) from interview_messages where session_id=:s and message_type='candidate_answer'"),
                {"s": sid})).scalar()
            return json.loads(state), rows
        else:
            await db.execute(text("delete from v4_session_state where session_id=:s"), {"s": sid})
            await db.execute(text("delete from interview_sessions where id=:s"), {"s": sid})
            await db.commit()
            left = (await db.execute(text(
                "select count(*) from interview_sessions where id=:s"), {"s": sid})).scalar()
            return left


def health(port: int) -> dict:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=10) as response:
        return json.load(response)


async def interview(ports, sid, token, proxy, outage_after, log):
    pids: list = []
    numbers: list[int] = []
    sent: list[str] = []
    notes: list[str] = []

    def saw(number, where):
        numbers.append(number)
        log(f"  question {number}  ({where}, worker {pids[-1] if pids else '?'})")

    client = await Client(ports, sid, token, pids).connect()
    await client.send("start_interview", session_id=sid)
    reply = await client.reply()
    assert reply["type"] == "question", reply
    saw(reply["question"]["number"], "start")

    redis_up = True
    final = None
    for turn, answer in enumerate(ANSWERS, 1):
        # Every turn on a fresh connection, which may land on the other worker.
        await client.close()
        client = await Client(ports, sid, token, pids).connect()
        await client.send("get_status", session_id=sid)
        snapshot = await client.reply()
        assert snapshot["type"] == "status_snapshot", snapshot
        saw(snapshot["question_number"], "reconnect")

        if turn == 2 and redis_up:  # drop the connection while the answer is being processed
            await client.send("submit_answer", candidate_answer=answer)
            assert (await client.next())["phase"] == "evaluating"
            await client.close()
            sent.append(answer)
            before = snapshot["question_number"]
            client = await Client(ports, sid, token, pids).connect()
            deadline = time.time() + 120
            while time.time() < deadline:
                await client.send("get_status", session_id=sid)
                snapshot = await client.reply()
                saw(snapshot["question_number"], "after dropping mid-turn")
                if snapshot["question_number"] > before:
                    break
                await asyncio.sleep(3)
            assert snapshot["question_number"] == before + 1, "the dropped turn was not completed exactly once"
        else:
            duplicate_due = turn == 3 and redis_up
            for _ in range(30):
                await client.send("submit_answer", candidate_answer=answer)
                assert (await client.next())["phase"] == "evaluating"
                if duplicate_due:  # the same answer again, from a second connection
                    await asyncio.sleep(1.0)
                    other = await Client(ports, sid, token, pids).connect()
                    await other.send("submit_answer", candidate_answer=answer)
                    second = await other.reply()
                    await other.close()
                reply = await client.reply()
                if reply.get("code") != "busy":
                    break
                # The previous turn is saved but still finishing: the server refuses, so send again.
                notes.append(f"answer {turn}: busy while the previous turn finished, sent again")
                await asyncio.sleep(3)
            if duplicate_due:
                notes.append(f"duplicate submit -> {second.get('type')}/{second.get('code')}")
                assert second.get("code") == "busy", second
            assert reply["type"] in ("evaluation", "report", "report_pending"), reply
            sent.append(answer)
            if reply["type"] == "evaluation":
                saw(reply["next_question"]["number"], f"answer {turn}")
            else:
                final = reply
                notes.append(f"last answer -> {reply['type']}")
                if reply["type"] == "report_pending":
                    started = time.time()
                    ready = await client.next(timeout=300)
                    assert ready["type"] == "report_ready", ready
                    notes.append(f"report_ready pushed {time.time() - started:.1f}s later")
                break

        if outage_after and turn == outage_after:
            proxy.cut()
            redis_up = False
            log(f"--- Redis stopped after answer {turn} ---")
            status = await asyncio.to_thread(health, ports[0])
            notes.append(f"/health during the outage: redis={status['redis']}")

    await client.close()
    return pids, numbers, sent, notes, final


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outage-after", type=int, default=0, help="cut Redis after this many answers")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--servers", type=int, default=1, help="more than 1: that many one-worker processes")
    args = parser.parse_args()

    from app.auth.interview_access import create_interview_access_token

    proxy = RedisProxy(ENV["REDIS_URL"])
    proxy_url = await proxy.start()
    ports = [free_port() for _ in range(max(1, args.servers))]
    workers = args.workers if args.servers <= 1 else 1
    server_logs = [Path(tempfile.gettempdir()) / f"aura-acceptance-{port}.log" for port in ports]
    env = {
        **os.environ,
        "REDIS_URL": proxy_url,
        "SESSION_STORE_BACKEND": "redis",
        "OPENROUTER_STRONG_MODEL": "openai/gpt-oss-20b",
        "GROQ_STRONG_MODEL": "openai/gpt-oss-20b",
        "ANTI_CHEAT_GUARD_ENABLED": "false",
        "PYTHONUNBUFFERED": "1",
    }
    sid = str(uuid.uuid4())
    log = lambda line: print(line, flush=True)
    servers = [
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port),
             "--workers", str(workers)],
            env=env, stdout=log_file.open("w"), stderr=subprocess.STDOUT,
        )
        for port, log_file in zip(ports, server_logs)
    ]
    created = False
    try:
        deadline = time.time() + 300
        for port, server, log_file in zip(ports, servers, server_logs):
            while True:
                try:
                    status = await asyncio.to_thread(health, port)
                    break
                except OSError:
                    assert server.poll() is None and time.time() < deadline, f"server did not start, see {log_file}"
                    await asyncio.sleep(2)
            log(f"server up, --workers {workers}: redis={status['redis']} session_store={status['session_store']}")
            assert status["redis"] == "ok" and status["session_store"] == "redis"
        await asyncio.sleep(20)  # let the second worker finish starting
        await database("create", sid)
        created = True

        pids, numbers, sent, notes, final = await interview(
            ports, sid, create_interview_access_token(uuid.UUID(sid)), proxy, args.outage_after, log)

        state, rows = await database("read", sid)
        said = [e["content"] for e in state["conversation_history"] if e.get("role") == "user"]
        checks = {
            "the interview finished": final is not None and state.get("finalized") is True,
            "the question number never went back": numbers == sorted(numbers),
            "every answer is in the history exactly once": len(said) == len(sent) == len(set(said)),
            "one stored answer row per answer": rows == len(sent),
        }
        log("")
        for note in notes:
            log(note)
        log(f"question numbers seen: {numbers}")
        log(f"answers sent: {len(sent)}, in history: {len(said)}, answer rows: {rows}")
        log(f"connections per worker: { {p: pids.count(p) for p in set(pids)} }")
        for name, ok in checks.items():
            log(f"{'PASS' if ok else 'FAIL'}  {name}")
        for log_file in server_logs:
            text = log_file.read_text(errors="replace")
            log(f"server log: {log_file}  (tracebacks: {text.count('Traceback')}, "
                f"Redis fallback warnings: {text.count('using the fallback')})")
        return 0 if all(checks.values()) else 1
    finally:
        for server in servers:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(server.pid)], capture_output=True)
            else:
                server.terminate()
        if created:
            log(f"test session deleted (rows left: {await database('delete', sid)})")
        # Remove this run's keys from the hosted Redis.
        from redis import Redis

        direct = Redis.from_url(ENV["REDIS_URL"], decode_responses=True)
        direct.delete(f"aura:sess:{sid}", f"aura:lock:{sid}", f"aura:llm:budget:session:{sid}",
                      f"aura:events:queued:{sid}")
        direct.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
