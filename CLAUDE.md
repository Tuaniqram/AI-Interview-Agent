# AI Interview Agent — working notes for Claude

## What this is
FastAPI backend + React frontend (`frontend/`) for an AI interviewer. A candidate answers ~14 questions over a WebSocket
(`app/api/interview_ws.py`); the engine scores each answer, picks the next question, and at the end produces a hiring report.

## Active work: follow the plan
- `docs/PROBLEMS_AND_SOLUTIONS.md` — what is wrong and why (P1–P12, N1–N9), with test evidence.
- `docs/IMPLEMENTATION_PLAN.md` — the numbered steps. **Do them in order, one commit per step, and do not start a step until the
  previous step's harness gate passes.**
- `docs/PROMPTS.md` — the full new prompt templates each step installs. Copy them exactly; do not improvise prompt changes.
- **Ask the user before any change to what the candidate sees or hears** (question style, difficulty behaviour, clarifications,
  timing) that the plan does not already list as approved.

## Architecture (where things live)
- `app/engine/` — orchestration. `engine.py` (entry), `lifecycle.py` (session start), `answer_processor.py` (per answer:
  sanitize → clarification → anti-cheat → evaluate → evidence), `routing.py` (reflection → director → hypotheses → difficulty →
  next question), `decision.py` (finalization chain), `builders.py` (response/report payloads), `persistence.py`.
- `app/agents/` — capabilities, plain `state dict in → state dict out`:
  - `evaluation/` — `candidate_evaluator.py` (LLM scores one answer), `scoring.py` (deterministic composite), `synthesis.py`,
    `evidence_reading.py` (final semantic read).
  - `reasoning/` — `evidence_engine.py` (evaluation → evidence records, competency summary), `hypothesis_engine.py` (Bayesian
    beliefs), `contradiction_engine.py` (sufficiency, canonical score), `reflection_engine.py`.
  - `decision/` — `director.py` (next action), `decision_engine.py` (7-point verdict), `decision_review.py`, `hiring_decision.py`.
  - `planning/` — `difficulty_engine.py`, `competency_planner.py`, `strategy_planner.py`.
  - `generation/` — `question_generator.py` (+ similarity guard, memory).
- `app/brain/` — the "AURA V5" layers recomputed each turn (`assembler.refresh_brain_layers`): question strategy, contradiction /
  seniority risk, calibration, candidate memory.
- `app/core/interview_brain.py` — the single state object. Stored as JSON (no DB migration for new fields), but **a new field must
  be declared on the dataclass** or `sync_from_dict` silently drops it.
- `prompts/` — Markdown templates with `{{var}}` placeholders, rendered by `app/services/prompt_loader.load_prompt`.
- `app/models/llm.py` — model chains: strong (OpenRouter gpt-oss-120b → Groq → free → local) and cheap (gpt-oss-20b first).

## Conventions
- **Deterministic code decides; the LLM reads and writes text.** Verdicts, scores, caps and next steps are computed in Python.
  LLM output is parsed defensively (`app/intelligence/_helpers.parse_json`) and a failure must degrade to the deterministic path,
  never crash a turn.
- Candidate text is untrusted: fence it as data in prompts, never let it act as instructions.
- Difficulty scale is 1–5 everywhere.
- Every change to the verdict path records *why* (the `adjustments` list from plan step 3 onward).
- New prompt variables must be passed by the caller; `tests/test_prompt_integrity.py` fails on unrendered `{{…}}`.

## Testing
- Unit tests: `venv/Scripts/python.exe -m pytest -q` (≈865 tests, ~1 min). Must pass after every change.
- Simulated interviews (real LLM calls, in memory, nothing written to the DB):
  `venv/Scripts/python.exe tools/interview_sim/run.py strong bluffer weak awkward -q 14 --out tools/interview_sim/out/<name>`
  then `venv/Scripts/python.exe tools/interview_sim/summarize.py tools/interview_sim/out/<name>/*`.
  - Always `-q 14`. One run per persona is noise: repeat (≥2) before trusting a change.
  - Discard runs whose log shows 429s or crashes. Output folders are git-ignored.
  - Personas: `strong` (should be hired), `bluffer` (fluent, made-up numbers — must not be hired), `weak` (junior — no hire),
    `awkward` (nervous but decent — must not get `no_hire`).

## Environment
- Windows; use the `venv/Scripts/python.exe` interpreter. Git Bash and PowerShell both available.
- `.env` holds `DATABASE_URL` (Supabase), `OPENROUTER_API_KEY` (paid, small balance — keep test rounds modest), `GROQ_API_KEY`
  (free tier, 200k tokens/day per model — backup only).
- Work on branch `dev`; `main` is for merges after the plan's final acceptance.
