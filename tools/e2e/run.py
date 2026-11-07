"""One-command browser end-to-end run.

    python tools/e2e/run.py                 # run the application-flow suite, then clean up test data
    python tools/e2e/run.py --pooler        # use the IPv4 Supabase pooler (no IPv6 on this machine)
    python tools/e2e/run.py --keep-data     # leave the e2e rows in the database for inspection
    python tools/e2e/run.py -- --headed     # extra arguments go to `playwright test`

What it does: starts the backend with mail capture (tools/e2e/server.py), waits until it is ready,
runs Playwright (which starts the Vite dev server itself), then stops the backend and removes the
test data (tools/e2e/cleanup.py). Needs: a configured .env (database, LLM keys), `npm install` in
frontend/, and Playwright's Chromium (`npx playwright install chromium`).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "frontend"
BACKEND_URL = "http://127.0.0.1:8000/openapi.json"


def wait_for(url: str, timeout: float, label: str, proc: subprocess.Popen | None = None) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise SystemExit(f"{label} exited early (code {proc.returncode}); see its log output above")
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            pass
        time.sleep(2)
    raise SystemExit(f"{label} did not become ready within {int(timeout)}s")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pooler", action="store_true", help="use the IPv4 Supabase pooler for this run")
    parser.add_argument("--keep-data", action="store_true", help="do not delete the e2e test data afterwards")
    parser.add_argument("--spec", default="e2e/application-flow.spec.ts", help="Playwright spec to run")
    args, passthrough = parser.parse_known_args()
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        raise SystemExit("npx not found: install Node.js and run `npm install` in frontend/")

    python = sys.executable
    venv_python = REPO / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if venv_python.exists():
        python = str(venv_python)

    workdir = Path(tempfile.mkdtemp(prefix="aura-e2e-"))
    mail_file = workdir / "mails.jsonl"
    mail_file.touch()
    env = {**os.environ, "E2E_MAIL_FILE": str(mail_file), "E2E_SHOTS": str(workdir)}
    if args.pooler:
        env["E2E_USE_POOLER"] = "1"

    print(f"[e2e] working dir: {workdir}")
    backend = subprocess.Popen([python, "-W", "ignore", str(REPO / "tools/e2e/server.py")], cwd=REPO, env=env)
    exit_code = 1
    try:
        print("[e2e] waiting for the backend (model warm-up can take a minute)...")
        wait_for(BACKEND_URL, 240, "backend", backend)
        print("[e2e] backend ready; running Playwright")
        result = subprocess.run(
            [npx, "playwright", "test", args.spec, "--reporter=list", "--workers=1",
             f"--output={workdir / 'pw-output'}", *passthrough],
            cwd=FRONTEND, env=env,
        )
        exit_code = result.returncode
    finally:
        backend.terminate()
        try:
            backend.wait(timeout=15)
        except subprocess.TimeoutExpired:
            backend.kill()
        if args.keep_data:
            print("[e2e] --keep-data: test rows left in the database (tools/e2e/cleanup.py removes them)")
        else:
            print("[e2e] removing test data")
            subprocess.run([python, "-W", "ignore", str(REPO / "tools/e2e/cleanup.py")], cwd=REPO, env=env)
        print(f"[e2e] screenshots and traces: {workdir}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
