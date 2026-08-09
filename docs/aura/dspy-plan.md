# DSPy Integration Plan (AURA) — SPIKE + PILOT

Status: **draft — under discussion (2026-08-09)**
Scope decision: **spike + pilot only** (resume analysis), then reassess before
touching anything else.

---

## 1. Why DSPy, and why here

Today the AURA engine's LLM layer is:

    prompts/*.md (prompt_loader.py)
      -> LLMService.invoke (cache + tiers + retries)
        -> parse_llm_json_with_retry (guess-and-retry JSON)
          -> deterministic/heuristic fallback

DSPy (github.com/stanfordnlp/dspy, MIT, DSPy 3.0 = production-grade, July 2026)
replaces the middle of that chain:

- **Typed signatures instead of brittle JSON.** A signature like
  `resume_text, job_role -> strengths: list[str], weaknesses: list[str], skills: list[str]`
  makes the prompt, parses the output into a typed `Prediction`, and
  auto-repairs malformed output. Directly replaces `parse_llm_json_with_retry`.
- **Native async** — `acall()` / `aforward()` on every module; fits the
  FastAPI engine without blocking.
- **Local-model friendly** — routes through litellm; any OpenAI-compatible
  endpoint drops in:
  `dspy.LM("openai/one", api_base="http://localhost:20128/v1", api_key="sk-no-key")`.
  Our `localhost:20128` server (models: `one`, `coder`, `fallback`, `nvidia`)
  qualifies.
- **Optimizers** (MIPROv2 / SIMBA / GEPA) compile better prompts from a small
  labeled set — a compiled prompt on the local 8B model often beats a
  hand-written one.

**AURA philosophy is preserved:** DSPy only *enriches*. Every deterministic
fallback stays. Downgrade-only honesty (calibration, `effective_claim`,
`cross_answer_risk`) is untouched — DSPy never claims credit; it just makes
the LLM enrichment branch more reliable.

---

## 2. Scope

### In scope (this work)

1. **Spike script** — prove DSPy works against the local model, async, typed.
2. **Pilot module** — `app/intelligence/resume_analyzer.analyze_resume` LLM
   branch converted to a DSPy module; profile/heuristic merge + fallback
   unchanged.
3. **Tests** — contract tests (typed shape; fallback when LM unreachable;
   deterministic merge unchanged). Full suite must stay green.
4. **Guardrails + docs** — pin `dspy`, save compiled programs under
   `dspy_programs/`, update this plan + CHANGELOG.

### Out of scope (until reassess)

- Other 13 LLM consumers (`role_competency_profiler`,
  `company_intelligence_builder`, `interview_blueprint_builder`,
  `strategy_planner`, question generation, answer evaluation, synthesis, …).
- Removing `parse_llm_json_with_retry` / `prompt_loader` markdown.
- `dspy.BaseLM` adapter that routes through `LLMService` (cache/tier/Redis).
- Full optimizer compile loop in CI.

---

## 3. Execution steps

### Step 1 — Spike (`scripts/dspy_spike.py`, local tool, scripts/ is gitignored)

- `pip install "dspy>=3.0"` — verify no clash with pinned `openai>=2.45.0`
  and langchain deps (DSPy pulls litellm; risk: openai-SDK version friction).
- Configure `dspy.LM("openai/one", api_base="http://localhost:20128/v1",
  api_key="sk-no-key")`.
- Run an **async** typed `dspy.Predict` on Alex Rivera's resume; print typed
  `Prediction`, latency, auto-repair behavior.
- Optional: `MIPROv2` compile on ~5 labeled examples to confirm the optimizer
  runs on the local model.
- **Exit criteria:** typed fields parse, `acall()` works, latency sane.

### Step 2 — Pilot (`app/intelligence/resume_analyzer.py`)

- New `app/intelligence/dspy_modules.py`:
  - `ResumeAnalysis(dspy.Signature)` — typed fields.
  - `ResumeAnalyzerProgram(dspy.Module)` with `aforward()`.
- Replace **only** the LLM-enrichment branch (`resume_analyzer.py:53-79`):
  `await module.acall(resume_text=..., job_role=...)` instead of
  `parse_llm_json_with_retry`.
- **Untouched:** profile+heuristic merge, `source` semantics, and the
  `except -> source="heuristics"` fallback. `LLMService` stays for other
  consumers.
- DSPy talks to the LM directly (bypasses LLMService caching for now — see
  Open questions).

### Step 3 — Tests

- Contract tests following `tests/test_intelligence.py` + the existing
  skip-when-no-LLM convention:
  - typed field shape (lists stay lists, years coerces to int);
  - `analyze_resume` returns `source="heuristics"` when LM unreachable
    (point LM at a dead port / monkeypatch);
  - deterministic merge unchanged.
- Full `pytest` must stay green (currently 592 passed).

### Step 4 — Report & reassess

- Sample output vs current `parse_llm_json_with_retry` path: field coverage,
  parse failures, latency.
- Decision gate before broadening to other consumers.

---

## 4. Guardrails

- **Deterministic-first:** DSPy enriches; all fallbacks preserved. If the DSPy
  call raises, behavior is byte-identical to today's heuristics path.
- **No secrets in code:** LM config reads existing env vars; local model uses
  `sk-no-key`.
- **Reproducibility:** compiled programs saved under `dspy_programs/`;
  `dspy` pinned in `requirements.txt`.
- **No new data exposure:** nothing here touches the (currently unauth'd)
  `GET /intelligence/brain/{sid}` endpoint — that is a separate security item.

---

## 5. Open questions for discussion

1. **LM routing:** DSPy modules talk to the local model directly. Do we later
   want a `dspy.BaseLM` adapter that routes through `FallbackLLM`/`LLMService`
   so cache/tier/Redis + the Groq/OpenRouter fallback chain still apply?
   (Recommend: yes, as a follow-up after the spike.)
2. **Optimizer runs:** MIPROv2 compile is slow/expensive. Keep it strictly
   offline in a script (like `build_brain_demo.py`)? Or add a `--compile`
   flag to the spike? (Recommend: offline script.)
3. **Which signature richness:** typed lists (`list[str]`) vs scalar fields
   only — typed lists are more useful but stricter for a weak local model.
4. **Dependency risk:** DSPy 3.0 pulls litellm; confirm no clash with pinned
   `openai>=2.45`/langchain before committing to it.
5. **Fallback parity:** the LLM branch today merges LLM fields *over*
   heuristics (`result[key] = dedupe(data[key])`). Keep that merge exactly, or
   let DSPy own the full output object? (Recommend: keep the merge.)
6. **When the local model is down** (no LLM available at all), the pilot must
   behave exactly like today: heuristics, `source="heuristics"`. Confirm that's
   the contract.
