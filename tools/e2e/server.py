"""Backend for the browser end-to-end tests: the real app and real database, with two seams.

* Outgoing email is captured as JSON lines in $E2E_MAIL_FILE (guests get every link by email, so
  the tests follow the captured links).
* The fit-evaluation LLM and org-document retrieval are stubbed so evaluations are deterministic.
  Everything else (interview engine, interview LLM calls, database) is real.

Started by ``tools/e2e/run.py``; can also be run by hand:

    E2E_MAIL_FILE=mails.jsonl python tools/e2e/server.py
"""
import json
import os
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.chdir(REPO)

MAIL_FILE = os.environ["E2E_MAIL_FILE"]

# Machines without IPv6 cannot reach Supabase's IPv6-only direct host: opt in to the IPv4 pooler for
# this process only (the project's .env is not modified).
if os.environ.get("E2E_USE_POOLER") == "1":
    from dotenv import dotenv_values

    url = dotenv_values(REPO / ".env")["DATABASE_URL"]
    m = re.match(r"postgres(?:ql)?://([^:]+):(.+)@([^@:/]+):(\d+)/(\w+)$", url)
    _user, pwd, host, _port, db = m.groups()
    if "pooler.supabase.com" not in host:
        ref = host.split(".")[1]
        os.environ["DATABASE_URL"] = (
            f"postgresql://postgres.{ref}:{pwd}@aws-0-ap-southeast-2.pooler.supabase.com:6543/{db}"
        )

import app.services.email as email_mod  # noqa: E402


async def capture_send(to, subject, template_name, **variables):
    with open(MAIL_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"to": to, "subject": subject, "template": template_name, "vars": variables}) + "\n")
    return True


email_mod.send_email = capture_send

from app.marketplace import fit_evaluation as fe  # noqa: E402


async def stub_fit_llm(prompt):
    first = next((l.split(" | ")[0] for l in prompt.splitlines() if " | core | " in l or " | supporting | " in l), None)
    return {
        "fit_score": 7.4,
        "fit_summary": "Solid Python/API background that matches the role well.",
        "matched_competencies": [{"id": first, "evidence": "Built REST APIs in Python"}] if first else [],
        "missing_competencies": [],
        "resume_strengths": ["Python", "REST APIs"],
        "risks": ["No on-call experience listed"],
        "recommended_probes": ["Walk through a production incident you handled"],
    }


async def stub_org_rag(org_id, query):
    return "", 0, None


fe._call_llm = stub_fit_llm
fe._retrieve_org_context = stub_org_rag

import uvicorn  # noqa: E402
from app.main import app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
