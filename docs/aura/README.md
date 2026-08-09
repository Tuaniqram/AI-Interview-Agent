# AURA Engine — Documentation

> Last updated: 2026-08-09 · Tag: [AURA-1.0-baseline]

AURA (Adaptive Unified Reasoning Assistant) is the interview-intelligence engine of
AI-Interview-Agent. It runs adaptive, evidence-driven hiring interviews: every answer
is evaluated, turned into typed evidence, reasoned about through hypotheses, and
finalized into a defensible 7-point hiring decision — all with a determinism-first
architecture where LLM passes are optional enrichments, never the source of truth.

This folder is the **canonical reference for the interview engine**. It is the
grounding document for every future change: when a change is confirmed and tested,
it is appended to the changelog and the affected doc sections are updated with a new
tag. Nothing in here is rewritten from scratch — it evolves incrementally.

## Doc index

| File | Covers |
|---|---|
| `01-overview.md` | What AURA is, design principles, invariants |
| `02-architecture.md` | Layers, module map, data flow |
| `03-apis.md` | The exact API surface the interview flow uses (REST + WebSocket) |
| `04-schema.md` | DB tables + columns used by the flow (Tier A–E) |
| `05-files.md` | File-by-file map of the engine (with key symbols) |
| `06-prompts.md` | All prompt files, their purpose and injected variables |
| `07-interview-flow.md` | End-to-end walk from demo driver to brain view |
| `08-reasoning-core.md` | Hypotheses, evidence, uncertainty, contradictions, difficulty |
| `09-decision-engine.md` | Canonical score, decision score, review, verdicts |
| `10-knowledge-bases.md` | Taxonomy, role brain, company brain, resolution chain |
| `WAVE-PLAN.md` | Wave plan (T1-taxonomy / T2-scoring / T4-calibration-ranking) with completion status |
| `CHANGELOG.md` | Tagged, append-only ledger of accepted changes |

## Change workflow (mandatory)

1. A change is **discussed** against the relevant doc.
2. It is **implemented** and **verified** (unit/contract tests → optional
   integration/e2e → demo autopilot).
3. Once **confirmed**, append a `CHANGELOG.md` entry:

   ```
   ## [AURA-x.y][feature-tag] — YYYY-MM-DD
   - What changed, why, which files
   - Verification performed
   ```

4. Update the affected doc's `Last updated: … · Tag: …` header and patch the body.
5. `pytest` (fast unit+contract suite, no services) must stay green.

## Test contract

| Command | Scope | Requires |
|---|---|---|
| `pytest` | `tests/unit` + `tests/contract` (fast) | none |
| `pytest -m integration` | DB-backed flows | `DATABASE_URL` |
| `pytest -m e2e` | full demo autopilot | server + LLM + DB |
| `pytest -m llm` | LLM-touching tests | LLM service |

Targeted reruns: `pytest tests/unit/data/ tests/unit/intelligence/` (taxonomy/role
breadth), `pytest tests/unit/agents/decision/ tests/unit/agents/reasoning/
tests/unit/agents/evaluation/ tests/unit/brain/` (scoring/judgment).
