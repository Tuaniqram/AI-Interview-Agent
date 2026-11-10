"""End-to-end single-org demo.

Pipeline: candidate logs in, applies with a CV, the org reviews the application
and invites the candidate, the candidate accepts, then the real WebSocket engine
runs the interview. Results are written to:

  * tools/interview_sim/out/demo/run.json
  * frontend/public/demo-interview.html
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import websockets
from sqlalchemy import select, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "interview_sim"))
sys.path.insert(0, str(ROOT / "scripts"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from personas import PERSONAS  # noqa: E402

from app.database.session import get_session_factory  # noqa: E402
from app.models.db import InterviewSession, ItRole  # noqa: E402
from app.services.llm_service import get_llm_service  # noqa: E402

ORG_LOGIN = {"email": "nova@test.com", "password": "Admin123!"}
CANDIDATE = {"email": "candidate@test.com", "password": "Test123!", "name": "Test Candidate"}
ROLE_SLUG = "senior-backend-developer"
MAX_TURNS = 25
OUT_DIR = ROOT / "tools" / "interview_sim" / "out" / "demo"
HTML_PATH = ROOT / "frontend" / "public" / "demo-interview.html"


def log(message: str) -> None:
    print(message, flush=True)


async def lookup_role() -> ItRole:
    factory = get_session_factory()
    async with factory() as db:
        role = (await db.execute(select(ItRole).where(ItRole.slug == ROLE_SLUG))).scalar_one_or_none()
    if role is None:
        raise SystemExit(f"IT role {ROLE_SLUG!r} not found. Run scripts/seed_it_catalog.py first.")
    return role


async def role_competency_defs(role_id) -> list[dict]:
    """The role's catalog competencies, shaped for a scorecard/template."""
    from app.models.db import Competency, RoleCompetency

    factory = get_session_factory()
    async with factory() as db:
        rows = (await db.execute(
            select(RoleCompetency, Competency)
            .join(Competency, Competency.id == RoleCompetency.competency_id)
            .where(RoleCompetency.role_id == role_id, Competency.is_active.is_(True))
            .order_by(RoleCompetency.is_core.desc(), RoleCompetency.weight.desc(), Competency.id)
        )).all()
    defs = [
        {
            "id": comp.id,
            "name": comp.name,
            "category": comp.category or "general",
            "weight": float(rc.weight) if rc.weight is not None else 1.0,
            "max_score": 10.0,
        }
        for rc, comp in rows
    ]
    if defs:
        return defs
    return [
        {"id": "tech_core", "name": "Core technical", "category": "technical", "weight": 2.0, "max_score": 10.0},
        {"id": "tech_system_design", "name": "System design", "category": "technical", "weight": 1.5, "max_score": 10.0},
        {"id": "cog_problem_solving", "name": "Problem solving", "category": "cognitive", "weight": 1.5, "max_score": 10.0},
        {"id": "behav_communication", "name": "Communication", "category": "behavioral", "weight": 1.0, "max_score": 10.0},
        {"id": "behav_teamwork", "name": "Teamwork", "category": "behavioral", "weight": 1.0, "max_score": 10.0},
        {"id": "exp_project_depth", "name": "Project depth", "category": "experience", "weight": 1.0, "max_score": 10.0},
    ]


def answer_prompt(question: str, history: str) -> str:
    persona = PERSONAS["strong"]
    return (
        "You are a job candidate in a live interview for the role 'Senior Backend Developer' at Nova AI. "
        "Stay in character and reply only with what you would say out loud. No stage directions.\n\n"
        f"YOUR CV:\n{persona['cv']}\n\nHOW YOU BEHAVE:\n{persona['brief']}\n\n"
        f"CONVERSATION SO FAR:\n{history}\n\n"
        f"Interviewer question: {question}\n\nYour next reply:"
    )


async def candidate_reply(question: str, history: list[tuple[str, str]]) -> str:
    transcript = "\n".join(f"{who}: {content}" for who, content in history[-8:])
    for attempt in range(3):
        try:
            text_out = await get_llm_service().invoke(
                prompt=answer_prompt(question, transcript),
                temperature=0.8,
                max_tokens=350,
                tier="cheap",
            )
            if text_out and text_out.strip():
                return text_out.strip()
        except Exception as exc:  # noqa: BLE001 - keep the demo moving
            log(f"  answer generation failed ({attempt + 1}/3): {exc}")
            await asyncio.sleep(2)
    return (
        "On my last platform I started from the bottleneck: I measured the request path, moved hot reads "
        "to Redis with a short TTL, kept PostgreSQL as the source of truth, and made the slow writes "
        "idempotent background jobs. I documented the trade-offs and added dashboards for p95 latency "
        "and error rate. That cut the worst path from about 900 ms to 250 ms without weakening consistency."
    )


async def send_and_wait(ws, next_id, payload: dict, expected: set[str], timeout: float = 300.0) -> dict:
    payload = dict(payload)
    payload["_id"] = str(next_id())
    await ws.send(json.dumps(payload))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        message = json.loads(raw)
        if message.get("type") in expected:
            return message


def evaluation_summary(message: dict) -> dict:
    ev = message.get("evaluation") or {}
    scores = ev.get("scores") or {}
    scored = {k: v.get("score") for k, v in scores.items() if isinstance(v, dict) and v.get("score") is not None}
    return {
        "composite": ev.get("composite"),
        "scored": ev.get("scored"),
        "scores": scored,
        "strengths": [s for v in scores.values() if isinstance(v, dict) for s in (v.get("strengths") or [])],
        "weaknesses": [s for v in scores.values() if isinstance(v, dict) for s in (v.get("weaknesses") or [])],
        "clarification": bool(message.get("clarification")),
    }


async def table_counts(session_id: str, org_id: str, candidate_email: str, role_id: str) -> list[tuple[str, int | str]]:
    specs = [
        ("interview_sessions", "id = :sid"),
        ("interview_messages", "session_id = :sid"),
        ("interview_evaluations", "session_id = :sid"),
        ("evidence_store", "session_id = :sid"),
        ("hypotheses", "session_id = :sid"),
        ("interview_brain", "session_id = :sid"),
        ("interview_timeline", "session_id = :sid"),
        ("interview_intelligence", "session_id = :sid"),
        ("interview_events", "session_id = :sid"),
        ("v4_session_state", "session_id = :sid"),
        ("scorecard_results", "session_id = :sid"),
        ("public_interview_submissions", "session_id = :sid"),
        ("public_interviews", "org_id = :org"),
        ("organizations", "id = :org"),
        ("it_roles", "id = :role"),
        ("organization_documents", "org_id = :org"),
        ("audit_log", "org_id = :org"),
        ("candidate_profiles", "email = :candidate"),
        ("candidate_documents", "candidate_id = (SELECT id FROM candidate_profiles WHERE email = :candidate)"),
        ("scorecard_templates", "org_id = :org"),
        ("interview_templates", "org_id = :org"),
    ]
    params = {"sid": session_id, "org": org_id, "candidate": candidate_email, "role": role_id}
    factory = get_session_factory()
    out: list[tuple[str, int | str]] = []
    async with factory() as db:
        for table, where in specs:
            try:
                count = await db.scalar(text(f"SELECT count(*) FROM {table} WHERE {where}"), params)
                out.append((table, int(count or 0)))
            except Exception as exc:  # table may not exist in an older schema
                out.append((table, f"n/a ({type(exc).__name__})"))
    return out


def prompts_used(server_logs: list[Path]) -> list[str]:
    names: list[str] = []
    pattern = re.compile(r"Loaded prompt:\s*(.+?)\s+with\s+\d+\s+variables")
    for path in server_logs:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = pattern.search(line)
            if match and match.group(1) not in names:
                names.append(match.group(1))
    return names


def render_html(run: dict) -> str:
    esc = html.escape
    report = run["report"] or {}
    recommendation = report.get("hiring_recommendation") or {}
    decision = report.get("final_decision") or {}
    verdict = decision.get("verdict") or recommendation.get("verdict") or "unknown"
    score = recommendation.get("composite_score") or report.get("final_score")
    confidence = recommendation.get("confidence")
    evidence = report.get("v4_evidence_count") or report.get("evidence_collected")
    pipeline = run.get("pipeline") or {}
    scorecard = run.get("scorecard") or {}

    rows = []
    for turn in run["turns"]:
        ev = turn.get("evaluation") or {}
        scores = ", ".join(f"{k}: {v}" for k, v in (ev.get("scores") or {}).items()) or "not scored"
        rows.append(f"""
        <section class="turn">
          <div class="q"><span class="label">Q{turn['number']}</span> {esc(turn['question'])}</div>
          <div class="a"><span class="label">Candidate</span> {esc(turn['answer'])}</div>
          <div class="meta">Score: <strong>{esc(str(ev.get('composite') if ev.get('composite') is not None else 'not scored'))}</strong>
            <span class="muted">({esc(scores)})</span></div>
          {f'<div class="note">Interviewer follow-up: {esc(turn["follow_up"])}</div>' if turn.get('follow_up') else ''}
        </section>""")

    scorecard_rows = []
    for cid, entry in (scorecard.get("scores") or {}).items():
        if not isinstance(entry, dict):
            entry = {"score": entry}
        value = entry.get("normalized", entry.get("score"))
        name = entry.get("name") or cid
        scorecard_rows.append(
            f"<tr><td>{esc(str(name))}</td><td>{esc(str(value if value is not None else '—'))}</td>"
            f"<td>{esc(str(entry.get('evidence_count', '—')))}</td></tr>"
        )

    db_rows = "".join(
        f"<tr><td>{esc(name)}</td><td>{esc(str(count))}</td></tr>" for name, count in run["tables"]
    )
    prompt_rows = "".join(f"<li><code>{esc(name)}</code></li>" for name in run["prompts"]) or "<li>No prompt log captured.</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Demo interview · Nova AI</title>
<style>
  :root {{ --green:#0c6b58; --ink:#1a1a1e; --muted:#646b78; --line:#e2e2e8; --bg:#f6f7f4; --card:#fff; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.6 Archivo,-apple-system,'Segoe UI',Arial,sans-serif; }}
  main {{ max-width:920px; margin:0 auto; padding:40px 20px 64px; }}
  header {{ border-bottom:1px solid var(--line); padding-bottom:20px; margin-bottom:24px; }}
  h1 {{ margin:0 0 6px; font-size:26px; }}
  h2 {{ font-size:16px; margin:32px 0 12px; }}
  .muted {{ color:var(--muted); }}
  .pill {{ display:inline-block; background:rgba(12,107,88,.10); color:var(--green); border-radius:999px; padding:3px 10px; font-size:12px; font-weight:600; margin-right:6px; }}
  .hero {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:24px; display:flex; flex-wrap:wrap; gap:24px; align-items:center; }}
  .hero .big {{ font-size:34px; font-weight:800; color:var(--green); }}
  .hero .stat {{ min-width:120px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 20px; margin-bottom:12px; }}
  .turn {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px 20px; margin-bottom:12px; }}
  .label {{ font-size:11px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; color:var(--green); margin-right:8px; }}
  .q {{ font-weight:600; margin-bottom:10px; }}
  .a {{ white-space:pre-wrap; }}
  .meta {{ margin-top:10px; font-size:13px; }}
  .note {{ margin-top:8px; font-size:12px; color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); border-radius:12px; overflow:hidden; }}
  th,td {{ text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); font-size:13px; }}
  th {{ background:var(--bg); }}
  a {{ color:var(--green); font-weight:600; text-decoration:none; }}
  .links a {{ margin-right:16px; }}
  code {{ font-family:'IBM Plex Mono',Consolas,monospace; font-size:12px; }}
  ul {{ padding-left:20px; }}
</style>
</head>
<body>
<main>
  <header>
    <div class="pill">Demo interview</div>
    <h1>{esc(run['org_name'])} · {esc(run['job_role'])}</h1>
    <div class="muted">Candidate: {esc(run['candidate_name'])} ({esc(run['candidate_email'])}) · {esc(run['started_at'])} · session <code>{esc(run['session_id'])}</code></div>
  </header>

  <section class="hero">
    <div class="stat"><div class="muted">Verdict</div><div class="big">{esc(str(verdict))}</div></div>
    <div class="stat"><div class="muted">Score</div><div class="big">{esc(str(score if score is not None else '—'))}</div></div>
    <div class="stat"><div class="muted">Confidence</div><div class="big">{esc(str(round(float(confidence) * 100) if confidence is not None else '—'))}%</div></div>
    <div class="stat"><div class="muted">Evidence</div><div class="big">{esc(str(evidence if evidence is not None else '—'))}</div></div>
  </section>

  <h2>Hiring pipeline</h2>
  <div class="card">
    <p><strong>Application:</strong> {esc(str(pipeline.get('application_id') or '—'))}</p>
    <p><strong>CV:</strong> {esc(str(pipeline.get('resume_filename') or '—'))} · uploaded={esc(str(pipeline.get('has_resume')))}</p>
    <p><strong>Fit evaluation:</strong> {esc(str(pipeline.get('fit_status') or '—'))}</p>
    <p><strong>Organization decision:</strong> invited · <strong>Candidate response:</strong> accepted</p>
    <p><strong>Template:</strong> {esc(str(pipeline.get('template_name') or '—'))} · <strong>Scorecard:</strong> {esc(str(pipeline.get('scorecard_name') or 'Built-in AURA'))}</p>
  </div>

  {f'''<h2>Scorecard</h2>
  <div class="card">
    <p><strong>{esc(str(scorecard.get('template_name') or 'Built-in AURA'))}</strong> · weighted score
    <strong>{esc(str(scorecard.get('weighted_score') if scorecard.get('weighted_score') is not None else '—'))}/10</strong></p>
    <table><thead><tr><th>Competency</th><th>Score</th><th>Evidence</th></tr></thead>
    <tbody>{''.join(scorecard_rows)}</tbody></table>
  </div>''' if scorecard else ''}

  <h2>Transcript</h2>
  {''.join(rows)}

  <h2>Database rows used</h2>
  <table><thead><tr><th>Table</th><th>Rows</th></tr></thead><tbody>{db_rows}</tbody></table>

  <h2>Prompts loaded during the run</h2>
  <ul>{prompt_rows}</ul>

  <h2>Open the live pages</h2>
  <p class="links">
    <a href="/interview/{esc(run['session_id'])}/report">Interview report</a>
    <a href="/org">Organization dashboard</a>
    <a href="/org/applications">Organization applications</a>
    <a href="/candidate/dashboard">Candidate dashboard</a>
  </p>
</main>
</body>
</html>"""


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-log", action="append", default=[], help="server log file to scan for prompts")
    args = parser.parse_args()

    get_llm_service()._cache_enabled = False
    role = await lookup_role()
    competencies = await role_competency_defs(role.id)
    log(f"role: {role.name} ({role.id}), competencies={len(competencies)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    from generate_demo_assets import build_resume

    cv_path = OUT_DIR / "candidate_cv.pdf"
    build_resume().output(str(cv_path))
    log(f"CV: {cv_path} ({cv_path.stat().st_size / 1024:.1f} KB)")

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=180) as client:
        login = await client.post("/api/v1/auth/login", json=ORG_LOGIN)
        login.raise_for_status()
        auth = login.json()
        token = auth["tokens"]["access_token"]
        org = auth["memberships"][0]
        org_id = org["org_id"]
        headers = {"Authorization": f"Bearer {token}", "X-Org-Id": org_id}
        log(f"org: {org['org_name']} ({org_id})")

        cand_login = await client.post("/api/v1/candidates/login", json={
            "email": CANDIDATE["email"], "password": CANDIDATE["password"],
        })
        cand_login.raise_for_status()
        cand_token = cand_login.json()["tokens"]["access_token"]
        cand_headers = {"Authorization": f"Bearer {cand_token}"}
        log(f"candidate: {CANDIDATE['email']} logged in")

        scorecard_resp = await client.post(f"/api/v1/orgs/{org_id}/scorecards", headers=headers, json={
            "name": "Senior Backend Scorecard",
            "competencies": competencies,
        })
        scorecard_resp.raise_for_status()
        scorecard_template = scorecard_resp.json()
        log(f"scorecard: {scorecard_template['id']} ({scorecard_template['name']})")

        template_resp = await client.post(f"/api/v1/orgs/{org_id}/templates", headers=headers, json={
            "name": "Senior Backend Interview Template",
            "job_role": role.name,
            "total_questions": 14,
            "interview_style": "AURA",
            "description": "Senior backend interview template for Nova AI.",
            "competencies": competencies,
            "scorecard_template_id": scorecard_template["id"],
        })
        template_resp.raise_for_status()
        template = template_resp.json()
        log(f"template: {template['id']} ({template['name']})")

        listing_resp = await client.post("/api/v1/marketplace/interviews", headers=headers, json={
            "title": "Senior Backend Developer",
            "it_role_id": str(role.id),
            "template_id": template["id"],
            "description": "Build and operate the interview platform backend: FastAPI services, PostgreSQL, Redis, async processing and reliability.",
            "interview_mode": "typing",
            "max_candidates": 50,
            "skills_required": "Python, FastAPI, PostgreSQL, Redis, system design, testing",
        })
        listing_resp.raise_for_status()
        listing = listing_resp.json()
        log(f"published listing: {listing['id']}")

        with open(cv_path, "rb") as fh:
            apply_resp = await client.post(
                f"/api/v1/marketplace/interviews/{listing['id']}/apply",
                headers=cand_headers,
                files={"resume": (cv_path.name, fh, "application/pdf")},
            )
        apply_resp.raise_for_status()
        application = apply_resp.json()
        application_id = application["id"]
        log(f"applied: {application_id} has_resume={application.get('has_resume')} fit={application.get('fit_status')}")

        # Let the CV fit evaluation finish so the org decision is made on a real record.
        for attempt in range(40):
            apps_resp = await client.get(f"/api/v1/marketplace/org/{org_id}/applications", headers=headers)
            apps = apps_resp.json() if apps_resp.is_success else []
            current = next((a for a in apps if a["id"] == application_id), None)
            if current:
                application = current
                log(f"  fit status: {current.get('fit_status')} ({current.get('fit_score')})")
                if current.get("fit_status") not in ("pending", "running"):
                    break
            await asyncio.sleep(3)

        invite_resp = await client.post(f"/api/v1/marketplace/applications/{application_id}/invite", headers=headers)
        invite_resp.raise_for_status()
        invited = invite_resp.json()
        session_id = invited["session_id"]
        log(f"org invited candidate: application={application_id} status={invited.get('status')} session={session_id}")

        factory = get_session_factory()
        async with factory() as db:
            invite_token = await db.scalar(
                select(InterviewSession.invite_token).where(InterviewSession.id == uuid.UUID(session_id))
            )
        if not invite_token:
            raise SystemExit("invitation token was not created")

        accept_resp = await client.post(
            f"/api/v1/marketplace/application-invitations/{invite_token}/respond",
            json={"response": "accepted"},
        )
        accept_resp.raise_for_status()
        accepted = accept_resp.json()
        access = accepted["access_token"]
        session_id = accepted["session_id"]
        log(f"candidate accepted: session={session_id} status={accepted.get('status')}")

    turns: list[dict] = []
    report: dict = {}
    history: list[tuple[str, str]] = []
    started_at = datetime.now(timezone.utc)

    uri = f"ws://localhost:8000/ws/interview/{session_id}?access={access}"
    async with websockets.connect(uri, max_size=None, ping_interval=20, close_timeout=10) as ws:
        counter = 0

        def next_id():
            nonlocal counter
            counter += 1
            return counter

        first = await send_and_wait(ws, next_id, {"type": "start_interview", "session_id": session_id}, {"question", "error"})
        if first.get("type") == "error":
            raise SystemExit(f"start failed: {first.get('detail')}")
        question = first.get("question") or {}
        number = int(question.get("number") or 1)

        for _ in range(MAX_TURNS):
            question_text = question.get("text") or ""
            log("")
            log(f"Q{number}: {question_text}")
            answer = await candidate_reply(question_text, history)
            history.append(("Interviewer", question_text))
            history.append(("Candidate", answer))
            log(f"A{number}: {answer}")

            message = await send_and_wait(ws, next_id, {
                "type": "submit_answer",
                "session_id": session_id,
                "question_number": number,
                "question": question_text,
                "candidate_answer": answer,
            }, {"evaluation", "report", "error"})

            if message.get("type") == "error":
                raise SystemExit(f"submit failed: {message.get('detail')}")
            if message.get("type") == "report":
                report = message
                ev = {"composite": None, "scores": {}, "scored": True, "clarification": False}
                turns.append({
                    "number": number,
                    "question": question_text,
                    "answer": answer,
                    "evaluation": ev,
                    "follow_up": "",
                })
                log(f"REPORT: verdict={message.get('hiring_recommendation', {}).get('verdict')} "
                    f"score={message.get('hiring_recommendation', {}).get('composite_score')}")
                break

            ev = evaluation_summary(message)
            next_question = message.get("next_question") or {}
            turns.append({
                "number": number,
                "question": question_text,
                "answer": answer,
                "evaluation": ev,
                "follow_up": next_question.get("text") or "",
            })
            log(f"  score={ev.get('composite')} dims={ev.get('scores')} clarification={ev.get('clarification')}")

            if next_question.get("text"):
                question = next_question
                number = int(next_question.get("number") or number + 1)
            else:
                qmsg = await send_and_wait(ws, next_id, {"type": "request_question", "session_id": session_id}, {"question", "error"})
                if qmsg.get("type") == "error":
                    raise SystemExit(f"next question failed: {qmsg.get('detail')}")
                question = qmsg.get("question") or {}
                number = int(question.get("number") or number + 1)

    ended_at = datetime.now(timezone.utc)

    # The summary endpoint merges the engine report with the scorecard and context.
    # A long interview can outlive the org access token, so log in again first.
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=120) as client:
        relogin = await client.post("/api/v1/auth/login", json=ORG_LOGIN)
        if relogin.is_success:
            fresh = relogin.json()
            summary_headers = {
                "Authorization": f"Bearer {fresh['tokens']['access_token']}",
                "X-Org-Id": org_id,
            }
            summary_resp = await client.get(
                f"/interviews/{session_id}/summary", headers=summary_headers
            )
            if summary_resp.is_success:
                report = summary_resp.json()

    counts = await table_counts(session_id, org_id, CANDIDATE["email"], str(role.id))
    prompt_names = prompts_used([Path(p) for p in args.server_log])
    scorecard = report.get("scorecard") or {}

    run = {
        "org_name": org["org_name"],
        "org_id": org_id,
        "job_role": listing.get("title") or "Senior Backend Developer",
        "listing_id": listing.get("id"),
        "candidate_name": CANDIDATE["name"],
        "candidate_email": CANDIDATE["email"],
        "session_id": session_id,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "seconds": round((ended_at - started_at).total_seconds(), 1),
        "pipeline": {
            "application_id": application_id,
            "resume_filename": application.get("resume_filename") or cv_path.name,
            "has_resume": application.get("has_resume"),
            "fit_status": application.get("fit_status"),
            "fit_score": application.get("fit_score"),
            "org_decision": "invited",
            "candidate_response": "accepted",
            "template_name": template.get("name"),
            "scorecard_name": scorecard_template.get("name"),
        },
        "turns": turns,
        "report": report,
        "scorecard": scorecard,
        "tables": counts,
        "prompts": prompt_names,
    }

    run_path = OUT_DIR / "run.json"
    run_path.write_text(json.dumps(run, indent=2, default=str), encoding="utf-8")
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    HTML_PATH.write_text(render_html(run), encoding="utf-8")

    log("")
    log("Demo complete")
    log(f"  session: {session_id}")
    log(f"  turns: {len(turns)}")
    log(f"  verdict: {(report.get('final_decision') or {}).get('verdict') or report.get('hiring_recommendation', {}).get('verdict')}")
    log(f"  score: {report.get('hiring_recommendation', {}).get('composite_score') or report.get('final_score')}")
    log(f"  scorecard: {scorecard.get('template_name')} weighted={scorecard.get('weighted_score')}")
    log(f"  transcript: {run_path}")
    log(f"  demo html: {HTML_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
