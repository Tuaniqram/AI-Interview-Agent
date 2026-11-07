"""Practice-candidate harness: run the real interview engine against simulated candidates.

    python tools/interview_sim/run.py                      # every persona, 6 questions each
    python tools/interview_sim/run.py strong bluffer -q 8  # chosen personas
    python tools/interview_sim/run.py --role senior-backend-developer --out some/dir

What it does
  * loads the role's competencies from the database READ-ONLY (same catalog the live app uses);
  * runs the real engine and the real LLM chain fully in memory (DATABASE_URL is blanked for the
    engine, so no session, answer or evidence row is ever written);
  * lets an LLM play each persona's candidate and records the transcript, per-answer scores and
    the final verdict as Markdown + JSON, so two runs can be diffed before/after a change.

It costs real LLM calls (roughly 30+ per interview). Output goes to tools/interview_sim/out/
(git-ignored) unless --out is given.
"""
import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import dotenv_values  # noqa: E402

_DB_URL = (dotenv_values(ROOT / ".env").get("DATABASE_URL") or "").strip().strip('"')
os.environ["DATABASE_URL"] = ""  # the engine must never touch the real database
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from personas import PERSONAS  # noqa: E402


async def load_role(slug: str) -> tuple[str, str, list[dict]]:
    """(role_id, role_name, competency defs) read straight from the catalog tables."""
    import asyncpg

    m = re.match(r"postgres(?:ql)?(?:\+\w+)?://([^:]+):(.+)@([^@:/]+):(\d+)/([\w-]+)", _DB_URL)
    if not m:
        sys.exit("DATABASE_URL in .env is missing or not postgresql://user:pass@host:port/db")
    user, pwd, host, port, db = m.groups()
    conn = await asyncpg.connect(
        user=user, password=unquote(pwd), host=host, port=int(port), database=db,
        ssl="require", statement_cache_size=0, timeout=30,
    )
    try:
        role = await conn.fetchrow("select id, name from it_roles where slug=$1 and is_active", slug)
        if not role:
            sys.exit(f"unknown role slug: {slug}")
        rows = await conn.fetch(
            """select c.id, c.name, c.category, rc.weight, c.evidence_dimensions, c.default_min_evidence
               from role_competencies rc join competencies c on c.id = rc.competency_id
               where rc.role_id = $1 and c.is_active
               order by rc.is_core desc, rc.weight desc, c.id""",
            role["id"],
        )
    finally:
        await conn.close()
    defs = [
        {
            "id": r["id"], "name": r["name"], "category": r["category"],
            "weight": float(r["weight"]) if r["weight"] is not None else 1.0,
            "evidence_dimensions": list(r["evidence_dimensions"] or []),
            "default_min_evidence": r["default_min_evidence"],
        }
        for r in rows
    ]
    return str(role["id"]), role["name"], defs


def build_state(session_id, role_id, role_name, taxonomy, required, domain_label, persona, max_questions):
    from app.config.interview_styles import get_style

    style = get_style("STANDARD")
    return {
        "session_id": session_id,
        "job_role": role_name,
        "org_id": None,
        "it_role_id": role_id,
        "interview_style": style,
        "persona": style.get("persona", "friendly"),
        "difficulty_level": style.get("difficulty_range", (1, 3))[0],
        "candidate_profile": {"full_name": persona["cv"].split(" - ")[0].strip(), "headline": "", "strengths": [], "weaknesses": []},
        "resume_text": persona["cv"],
        "scorecard_competencies": [
            {"id": c["id"], "name": c.get("name", c["id"]), "weight": 1.0} for c in taxonomy
        ],
        "competency_taxonomy": taxonomy,
        "domain_label": domain_label,
        "required_competencies": required,
        "conversation_history": [],
        "question_number": 0,
        "current_question": "",
        "candidate_answer": "",
        "flow_type": "v5_evidence_driven",
        "nodes_executed": [],
        "start_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypotheses": [],
        "hypothesis_target": None,
        "evidence_store": [],
        "competency_summary": {},
        "unified_evaluation": {},
        "evaluation_score": None,
        "observations": [],
        "competency_plan": [],
        "next_competency": None,
        "interview_strategy": {},
        "reflection_action": "probe",
        "evidence_sufficiency": {},
        "hiring_recommendation": {},
        "contradictions": [],
        "consistency_checks": [],
        "extracted_evidence": [],
        "max_questions": max_questions,
        "questions_asked": [],
        "question_objective": {},
        "skip_evaluation": False,
        "evaluator_mode": style.get("evaluator_mode", "unified"),
        "strategy_cache_valid": False,
    }


USAGE = {"calls": 0, "chars": 0, "cheap_chars": 0, "strong_chars": 0, "sim": False}


def _install_usage_counter():
    """Count engine LLM calls and prompt size (~4 chars per token); simulated-candidate calls are excluded."""
    from app.services.llm_service import LLMService

    original = LLMService.invoke

    async def counted(self, prompt, *a, **kw):
        if not USAGE["sim"]:
            USAGE["calls"] += 1
            USAGE["chars"] += len(prompt or "")
            USAGE["cheap_chars" if kw.get("tier") == "cheap" else "strong_chars"] += len(prompt or "")
        return await original(self, prompt, *a, **kw)

    LLMService.invoke = counted


async def candidate_reply(persona: dict, role_name: str, transcript: list[tuple[str, str]]) -> str:
    """Let an LLM answer the interviewer's last message as this persona."""
    from app.services.llm_service import get_llm_service

    history = "\n".join(f"{who}: {text}" for who, text in transcript[-8:])
    prompt = (
        f"You are a job candidate in a live interview for the role '{role_name}'. "
        f"Stay in character and reply only with what you would say out loud - no stage directions.\n\n"
        f"YOUR CV:\n{persona['cv']}\n\nHOW YOU BEHAVE:\n{persona['brief']}\n\n"
        f"CONVERSATION SO FAR:\n{history}\n\nYour next reply:"
    )
    USAGE["sim"] = True
    try:
        text = await get_llm_service().invoke(prompt=prompt, temperature=0.9, max_tokens=300, tier="cheap")
    finally:
        USAGE["sim"] = False
    return (text or "").strip() or "I'm not sure."


async def run_one(name: str, persona: dict, role: tuple, questions: int, out_dir: Path) -> dict:
    from app.data.competency_resolver import taxonomy_for_state
    from app.engine.engine import InterviewEngine
    from app.services.v4_session_store import MemoryV4SessionStore

    role_id, role_name, defs = role
    from app.data.competency_resolver import _normalize

    taxonomy, required, domain_label = taxonomy_for_state(_normalize(defs))
    session_id = f"sim-{name}-{int(time.time())}"
    store = MemoryV4SessionStore(db_path=str(Path(tempfile.gettempdir()) / f"{session_id}.json"))
    engine = InterviewEngine(store=store)
    state = build_state(session_id, role_id, role_name, taxonomy, required, domain_label, persona, questions)

    started = time.perf_counter()
    turns: list[dict] = []
    transcript: list[tuple[str, str]] = []
    error = None
    report = None
    start_seconds = None
    try:
        t_start = time.perf_counter()
        resp = await engine.start_session(state, build_intelligence=True)
        start_seconds = round(time.perf_counter() - t_start, 1)
        question = resp.get("conversation_turn") or (resp.get("question") or {}).get("text", "")
        for _ in range(questions + 2):
            transcript.append(("Interviewer", question))
            answer = await candidate_reply(persona, role_name, transcript)
            transcript.append(("Candidate", answer))
            calls0, chars0 = USAGE["calls"], USAGE["chars"]
            cheap0, strong0 = USAGE["cheap_chars"], USAGE["strong_chars"]
            t0 = time.perf_counter()
            resp = await engine.process_answer(session_id, answer)
            took = time.perf_counter() - t0
            ev = resp.get("evaluation") or {}
            brain = resp.get("brain") or {}
            turns.append({
                "question": question, "answer": answer, "seconds": round(took, 1),
                "llm_calls": USAGE["calls"] - calls0, "approx_tokens": (USAGE["chars"] - chars0) // 4,
                "cheap_tokens": (USAGE["cheap_chars"] - cheap0) // 4,
                "strong_tokens": (USAGE["strong_chars"] - strong0) // 4,
                "score": ev.get("composite"), "scored": ev.get("scored"),
                "next_competency": (resp.get("next_question") or {}).get("target_competency"),
                "strategy": brain.get("question_strategy") or {},
            })
            if resp.get("status") == "completed" or resp.get("interview_complete"):
                report = resp
                break
            question = resp.get("conversation_turn") or (resp.get("next_question") or {}).get("text", "")
    except Exception as exc:  # noqa: BLE001 - a crash is a finding, record it
        import traceback

        error = "".join(traceback.format_exception(exc))[-2000:]

    result = {
        "persona": name, "label": persona["label"], "role": role_name,
        "seconds": round(time.perf_counter() - started, 1), "start_seconds": start_seconds, "turns": turns,
        "report": report, "error": error,
    }
    (out_dir / f"{name}.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    (out_dir / f"{name}.md").write_text(render_markdown(result), encoding="utf-8")
    return result


def render_markdown(r: dict) -> str:
    lines = [f"# {r['label']} - {r['role']}", f"_{len(r['turns'])} answers, {r['seconds']}s total, {r.get('start_seconds')}s to prepare the interview_", ""]
    for i, t in enumerate(r["turns"], 1):
        strat = (t["strategy"] or {}).get("question_strategy") or {}
        mode = strat.get("mode") or strat.get("probe_mode") or ""
        lines += [
            f"## Turn {i}", f"**Interviewer:** {t['question']}", "",
            f"**Candidate:** {t['answer']}", "",
            f"_score={t['score']} scored={t['scored']} next={t['next_competency']} mode={mode} ({t['seconds']}s, "
            f"{t.get('llm_calls')} LLM calls, ~{t.get('approx_tokens')} prompt tokens: "
            f"{t.get('cheap_tokens')} cheap + {t.get('strong_tokens')} strong)_", "",
        ]
    rep = r.get("report") or {}
    if rep:
        hd = rep.get("hiring_decision") or {}
        lines += [
            "## Result", f"- verdict: **{rep.get('verdict')}**", f"- decision: {hd.get('decision')} "
            f"(score {hd.get('decision_score')})", f"- coverage: {(rep.get('coverage') or {}).get('competency_coverage_ratio')}",
            f"- avg answer score: {(rep.get('interview_performance') or {}).get('average_answer_score')}",
            f"- hypotheses: {rep.get('hypothesis_outcomes')}", "",
        ]
    elif not r.get("error"):
        lines += ["## Result", "- interview did not reach a report within the turn limit", ""]
    if r.get("error"):
        lines += ["## CRASH", "```", r["error"], "```"]
    return "\n".join(lines)


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("personas", nargs="*", help="default: all")
    ap.add_argument("-q", "--questions", type=int, default=6)
    ap.add_argument("--role", default="backend-developer")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out"))
    args = ap.parse_args()

    names = args.personas or list(PERSONAS)
    bad = [n for n in names if n not in PERSONAS]
    if bad:
        sys.exit(f"unknown persona(s) {bad}; choose from {list(PERSONAS)}")
    out_dir = Path(args.out) / time.strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    _install_usage_counter()
    role = await load_role(args.role)
    print(f"role={role[1]} competencies={len(role[2])} -> {out_dir}")
    summary = []
    for n in names:
        print(f"... {n}", flush=True)
        r = await run_one(n, PERSONAS[n], role, args.questions, out_dir)
        rep = r["report"] or {}
        summary.append((n, len(r["turns"]), rep.get("verdict"), r["seconds"], "CRASH" if r["error"] else ""))
        print(f"    {len(r['turns'])} answers, verdict={rep.get('verdict')}, {r['seconds']}s {'CRASH' if r['error'] else ''}")
    (out_dir / "summary.txt").write_text("\n".join(map(str, summary)), encoding="utf-8")
    print(f"\ntranscripts: {out_dir}")


if __name__ == "__main__":
    asyncio.run(main())
