# 01 — AURA Overview

> Last updated: 2026-08-09 · Tag: [AURA-1.6][evidence-reading]

## What AURA is

AURA is a **hypothesis-driven interview conductor**. It does not just ask
questions — it forms beliefs about a candidate's competencies, probes those
beliefs with targeted questions, converts every answer into typed evidence, and
arrives at a **defensible, explainable hiring decision**. The single core prompt
(`prompts/brain_builder/core_reasoning_agent.md`) phrases it as: *"Your
responsibility is not to conduct a conversation. Your responsibility is to
discover truth about candidate capability."*

## Design principles

1. **Determinism first.** The brain layers in `app/brain/`, the scoring math in
   `app/agents/evaluation/scoring.py` and the decision math in
   `app/agents/decision/` are pure deterministic code. LLM passes (role profiler,
   evaluator, difficulty governor, question generator) are **optional
   enrichments** — when they fail or are disabled (`use_llm=False`), the engine
   falls back to deterministic layers and still completes correctly.
2. **Best-effort persistence.** DB writes are non-fatal. A database failure never
   breaks an interview; the in-memory V4 session store is authoritative during
   the session and the DB is a durable mirror/checkpoint.
3. **Evidence over claims.** Candidate claims are not scored; evidence of the
   claim (`demonstrated`/`proven` levels) is. High scores that were never
   stress-tested are flagged as unverified (`explainable_scoring_node`).
4. **One canonical score.** Every downstream component (report, synthesis,
   decision, persisted session) reads from the single `compute_canonical_score`
   formula so the report can never show competing truths.
5. **Single source of truth per session.** The `InterviewBrain`
   (`app/core/interview_brain.py`) is the authoritative reasoning state,
   reconciled to plain dicts only at the agent boundary.

## Key invariants (regression guards)

- An interview can **never finish before 5 answered questions**
  (`MIN_QUESTIONS_BEFORE_FINISH`).
- A competency is asked **at most 3 questions** (`MAX_QUESTIONS_PER_COMPETENCY`).
- Coverage/sufficiency targets **at most 6 required competencies**
  (`MAX_REQUIRED_COMPETENCIES`) so the question budget is not spread thin.
- Difficulty is **clamped to the role's seniority floor** and never ratcheted up
  while the calibration brain calls the evidence base shallow.
- **Decisions require a minimum evidence base** (`MIN_EVIDENCE_FOR_DECISION`);
  otherwise the verdict is `insufficient_evidence`.
- Strong answers can never lower difficulty; weak answers can never raise it.
- **Competencies are never randomly generated** by the LLM — the resolved
  taxonomy (scorecard → template → AI profiler → default) is authoritative; the
  role brain only assigns importance and probes to it.
- **LLM produces signals, deterministic engine applies them.** The evidence
  reading (AURA-1.6) classifies each answer's claims semantically, but only
  through the **downgrade-only** rule: the effective claim is
  `min(semantic, regex)` over mentioned < demonstrated < proven — the LLM can
  confirm or downgrade a claim, never inflate it past the deterministic floor.

## What the flow exercises (in one sentence)

`scripts/demo_autopilot.py` drives org login → marketplace listing → candidate
login → session start → WebSocket interview loop (`start_interview` +
`submit_answer`×N + `request_question`) → summary → persisted brain view.
