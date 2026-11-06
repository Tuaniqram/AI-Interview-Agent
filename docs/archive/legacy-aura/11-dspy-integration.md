# 11 — DSPy Integration (Resume Analysis Pilot)

> Last updated: 2026-08-10 · Tag: [AURA-1.7][dspy-pilot]

## What this is

A **spike + pilot** (not a migration) proving DSPy replaces the brittle
guess-and-retry JSON branch of resume analysis. DSPy only *enriches* — it never
touches the deterministic layers, `source` semantics, or the heuristics
fallback.

## The two-backend design (safety toggle)

Resume analysis now has **two optional LLM backends**, selected per-process by
an env var — no code change needed to flip:

| `RESUME_LLM_BACKEND` | Backend | Path |
|---|---|---|
| `dspy` **(default)** | `app/intelligence/dspy_modules.py` | typed `ResumeAnalysis` signature → `Prediction` → merge |
| `legacy` | `app/services/llm_service.py` + `prompt_loader` | `parse_llm_json_with_retry` (pre-DSPy path) |

Both backends feed the **same merge + coercion + fallback** block in
`analyze_resume`:

    try:
        data = await (dspy | legacy)  # selected by env
        # identical merge logic (dedupe lists, coerce years, source="resume_llm")
    except Exception:
        result["source"] = "heuristics"   # byte-identical to pre-DSPy behavior

- **Default = `dspy`.** When it raises (LM down, bad output), behavior is
  byte-identical to today: heuristics, `source="heuristics"`.
- **`legacy` is the operator kill switch**, not a chained fallback. DSPy →
  heuristics is already the deterministic safety net; chaining legacy in the
  middle would double failure latency and muddy `source` attribution. Flip
  `RESUME_LLM_BACKEND=legacy` to revert to the old path with zero redeploy.

## Files

| File | Role |
|---|---|
| `app/intelligence/dspy_modules.py` | `ResumeAnalysis` signature, `ResumeAnalyzerProgram` (`forward`/`aforward`), `run_resume_analysis` → dict |
| `app/intelligence/resume_analyzer.py` | `_use_dspy_backend()` switch; `_legacy_llm_parse()` (restored old path) |
| `scripts/dspy_spike.py` | Standalone spike: async typed `Predict` vs local gateway |
| `tests/test_dspy_modules.py` | Signature/program unit tests + `llm`-marked live test (self-skips when gateway down) |
| `tests/test_intelligence.py` | DSPy merge, DSPy fallback, legacy path, default-backend tests |

## Security posture

- **`dspy==3.3.0`** pinned (fixes CVE-2025-12695; we never use
  `PythonInterpreter` regardless).
- **`litellm` ≥ 1.83.10** (resolves to 1.96.0) — patches CVE-2026-42271 (RCE,
  on CISA KEV) and CVE-2026-42208 (SQLi). **Client-only**: never the litellm
  proxy, no `LITELLM_MASTER_KEY`.
- **diskcache CVE-2025-69872** (unsafe pickle, no upstream fix yet): every DSPy
  entry point calls `dspy.configure_cache(restrict_pickle=True)` — DSPy then
  deserializes via an allowlisted unpickler (`dspy/clients/disk_serialization.py`).
  Never the default unrestricted disk cache.
- **No secrets in code**: local gateway uses `sk-no-key`; override endpoint via
  `DSPY_BASE_URL` / `DSPY_MODEL`.

## Local gateway note

The `localhost:20128` gateway advertises `one`/`coder`/`fallback`/`nvidia`, but
those aliases have been flaky (`one` → 410, `coder`/`nvidia` → timeout).
`openrouter` reliably routes to the working NVIDIA backend — it is the default
`DSPY_MODEL`. Verified spike: typed fields parse, `acall()` works, ~40s latency
(reasoning model), `years_of_experience` coerced to `int`.

## Verification

- Full default suite green: **598 passed, 2 deselected** (`llm`-marked live
  test excluded; `pip-audit` clean for all DSPy-introduced leaves).
- `pytest -m llm tests/test_dspy_modules.py` exercises the real DSPy path when
  the gateway is up (self-skips otherwise).

## Reassessment gate (per dspy-plan.md)

Pilot stays limited to resume analysis until a report compares DSPy vs legacy:
field coverage, parse failures, latency. Other LLM consumers are out of scope.
