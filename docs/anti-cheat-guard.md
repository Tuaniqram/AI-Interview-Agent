# Anti-AI-Cheating Integrity Guard

> Last updated: 2026-08-14 · Version: 1.1 (contract draft)
> Scope: any frontend that submits answers and the engine answer-intake
> pipeline. This document is the **stable contract** — engine and frontend
> implement it, and future frontend rebuilds must not drift from it.

## 1. Purpose & philosophy

Candidates increasingly use AI tools (LLMs, side-panels, auto-responders) to
cheat in remote interviews. The guard detects plausible AI-assisted answers
without breaking the interview or penalizing honest candidates.

Intentionally chosen properties — do not regress these:

| Property | Value |
|---|---|
| Master switch | env-gated, **OFF by default** (developers keep testing with AI) |
| Failure mode | best-effort, never raises, never blocks the interview (same contract as `persist_evidence`) |
| Action on suspicion | **flag only** — no auto-fail, no interview interruption |
| Visibility | final report payload only; no live event-log spam |
| Telemetry | treated as *signals*, never proof (it is client-supplied and spoofable) |
| Cost | heuristics are free; the LLM judge is one LLM call per answer, only when enabled and the answer is long enough |

## 2. Status

1.1 = documented contract + implemented. Engine files:
`app/services/anti_cheat.py`, hook in `app/engine/answer_processor.py`,
`question_asked_at` timestamp stamping at question emission, report section in
`build_report_response`. Frontend: `frontend/src/utils/antiCheatTelemetry.ts`
(listeners + hardening signals), `ConductorRoom` (rules gate, flag gauge,
countdown, submit payload via `interviewController.ts`). Tests:
`tests/test_anti_cheat.py`.

## 3. Env configuration

All vars live in `.env.example` under the `# ----- Anti-cheat guard (default OFF) -----`
block. The backend **must** function identically when every var is absent.

| Var | Default | Effect |
|---|---|---|
| `ANTI_CHEAT_GUARD_ENABLED` | `false` | Master switch. `false` ⇒ `assess()` is a pass-through stub: zero LLM calls, zero state mutation. |
| `ANTI_CHEAT_LLM_JUDGE` | `true` | Run the LLM judge layer (see §6). Only consulted when the guard is enabled and answer length ≥ 200 chars. |
| `ANTI_CHEAT_FLAG_THRESHOLD` | `70` | Per-answer score ≥ threshold ⇒ that answer (and the aggregate) is `flagged: true`. |
| `ANTI_CHEAT_MAX_FLAGS` | `3` | Flagged answers tolerated before the session is terminated (see §7.4). |
| `ANTI_CHEAT_ANSWER_TIME_LIMIT_S` | `120` | Hard per-answer window surfaced in the integrity policy (0 = no UI countdown). |
| `ANTI_CHEAT_POINTER_LEAVE_THRESHOLD` | `3` | Pointer-leave events per question that score as possible second-screen reading. |
| `ANTI_CHEAT_TAMPER_DIVERGENCE_S` | `0.5` | Wall-clock vs rAF divergence (s) classified as a session-tamper gap. |

## 4. Frontend ↔ backend contract (immutable)

### 4.1 `submit_answer` WS payload (backend → engine input)

The existing message gains **optional** fields. The backend must work with
them absent — an older frontend, voice mode, or a stripped rebuild sends no
telemetry, and that simply means *no signal*, never an error.

```
submit_answer:
  type:              "submit_answer"        (existing)
  candidate_answer:  string                 (existing)
  paste_chars:       number | absent        (NEW, optional)
  focus_lost_count:  number | absent        (NEW, optional)
  answer_source:     "typing" | "voice" | absent
  keystroke_intervals: number[] | absent    (NEW §4.6)
  first_key_ms:      number | absent        (NEW §4.6)
  pointer_leaves:    number | absent        (NEW §4.6)
  heartbeat_gaps:    number | absent        (NEW §4.6)
```

- `paste_chars` — total chars inserted via clipboard paste while composing
  this answer.
- `focus_lost_count` — number of tab/visibility-loss events while this
  question was active (i.e. after the question was shown, before submit).
- `answer_source` — `"voice"` skips paste/typing-rate/cadence signals (a
  spoken answer cannot be copy-pasted or macro-typed).
- `keystroke_intervals` — inter-key intervals (ms) for the answer being
  composed (capped by the client); feeds the cadence signal (§5).
- `first_key_ms` — ms between the question appearing and the first keystroke.
- `pointer_leaves` — times the pointer exited the focused window (possible
  side-by-side-screen reading; debounced client-side).
- `heartbeat_gaps` — rAF/wall-clock divergences (debugger breakpoints, VM
  snapshots); an invariant a spoofing script must actively fake.

The WS handler (`app/api/interview_ws.py`) reads these and passes them to
`engine.process_answer(..., integrity_meta=...)`. `process_answer` forwards
them into the guard. Rendering, storage, and calculation of these values are
frontend concerns; the backend only consumes what it receives.

### 4.2 Report `integrity` section (backend output → frontend rendering)

On interview completion, `build_report_response` adds an `integrity` object
**only when at least one signal exists** (absent otherwise — frontends must
render its absence as "no signals recorded", never as a failure). Key names
are frozen at 1.0; a frontend rebuild must not rename or omit any of them.

```
integrity:
  score:    number   # aggregate 0–100 across the session (max per-answer score)
  flagged:  boolean  # aggregate: score >= ANTI_CHEAT_FLAG_THRESHOLD
  signals:  [        # one entry per evaluated answer, in answer order
    {
      question_number:   number
      score:             number   # 0–100 for this answer
      latency_secs:      number | null   # null when question_asked_at missing
      paste_hint:        boolean  # heuristic proxy (see §5)
      focus_losses:      number   # client-reported tab/blur losses (0 when absent)
      duplicate_ratio:   number   # 0–1 best match vs earlier answers in session
      pointer_leaves:    number   # §4.6 second-screen signal (0 when absent)
      heartbeat_gaps:    number   # §4.6 tamper signal (0 when absent)
      cadence_score:     number | null   # §4.6 keystroke-rhythm score (null for voice/absent)
      llm_ai_score:      number | null   # LLM judge 0–100; null when skipped/failed
      reasons:           string[] # human-readable bullet reasons for this answer
    }
  ]
```

### 4.3 Integrity policy (session start, frontend rules gate)

`integrity_policy` on the session-start/question payload drives the rules gate
and the live gauge:

```
integrity_policy:
  enabled:             boolean  # guard on
  max_flags:           number   # flag limit before termination (0 = none)
  flagged_count:       number   # current accumulated flags
  answer_time_limit_s: number   # §4.7 hard per-answer window (0 = no countdown)
```

### 4.4 Live flag gauge (per-turn evaluation payload)

Each answer response carries `integrity` (present only once the guard has a
signal): `{ flagged_count, max_flags, score }` — the frontend renders the
candidate-facing gauge from it. No surprises at termination time.

### 4.5 Termination on repeated flags

When `flagged_count` reaches `ANTI_CHEAT_MAX_FLAGS`, the engine finalizes the
session after evaluating the current answer fairly: no further question is
emitted, the `{type: report}` response carries `integrity_terminated: true`,
and the report section includes the termination reason.

### 4.6 Hardening telemetry (v1.1)

Three additional client signals counter the vectors a tab-switch log cannot
see. All are **optional**; a client sending none is judged on the classic
signals alone.

| Vector | Signal | Client behavior | Judge reaction |
|---|---|---|---|
| Typed transcription of AI answers / macro input | `keystroke_intervals` | inter-key ms log per answer (capped) | sustained mean < 125 ms with > 80% fast keys ⇒ cadence 92 (decisive); fast bursts + recurring 1.2–8 s look-up pauses with stable pause cadence ⇒ 55–72 |
| Side-by-side screen reading (tab stays focused) | `pointer_leaves` | debounced count of pointer exits from the focused window | ≥ threshold ⇒ 75; ≥ 2× ⇒ 90; 1–2 ⇒ 45 |
| Debugger breakpoints / VM snapshots | `heartbeat_gaps` | rAF vs wall-clock divergence > 500 ms (skipped while tab hidden) | 1 ⇒ 85 (decisive); ≥ 2 ⇒ 95 |
| AI-prepped answers on a second device | latency/typing-rate + session-context questions | — | questions reference the candidate's earlier statements/claims so a phone cannot carry prepared answers |

Scoring semantics: signals are blended with renormalized weights, then
**best-evidence-wins** — the strongest single signal sets a floor on the score
so a decisive machine-typing or tamper reading is never diluted below the flag
threshold by weak style noise.

### 4.7 Answer time-boxing

`ANTI_CHEAT_ANSWER_TIME_LIMIT_S` (surfaced via `integrity_policy.answer_time_limit_s`)
gives each question a hard answer window. The frontend shows a countdown and
auto-submits at expiry (skipping the question if nothing is typed). A short
window makes second-device lookup impractical; the judge independently
penalizes near-instant long answers (latency signal).

## 5. Signal catalog (heuristics — free pass)

Computed per answer in `app/services/anti_cheat.py::heuristic_signals()` and
merged by `assess()`. Heuristics never make network calls.

| Signal | Detects | How computed | Spoofable? |
|---|---|---|---|
| `response_latency_secs` | Near-instant polished answers (copy-paste from AI) | `now - question_asked_at`; `question_asked_at` is stamped by the engine at question emission (session start in lifecycle, each turn in routing) and persisted with brain state; null when absent | No (server time) |
| Text fingerprint | LLM-typical uniformity | burstiness (sentence-length variance), zero typo/filler rate, em-dash + markdown + code-fence density; no external libraries | Hard |
| `paste_hint` | Wholesale pasted answers | heuristic: perfect markdown structure + abrupt lead-in on an otherwise unformatted session; combined with client `paste_chars` when present | Yes |
| `duplicate_ratio` | Replayed/memorized answers | normalized difflib ratio vs the session's earlier answers (no embeddings infra) | No |
| Keystroke cadence | Transcribed/macro answers | mean interval, burst ratio, look-up-pause cadence from `keystroke_intervals` (§4.6) | Hard (must fake realistic human rhythm) |
| Pointer leaves | Second-screen reading | debounced pointer exits from the focused window (§4.6) | Hard (must synthesize events) |
| Tamper gaps | Debugger/VM interference | rAF vs wall-clock divergence (§4.6) | Very hard (a frozen page cannot send events) |
| Prompt injection | Candidates trying to hijack the interviewer LLM | existing `detect_prompt_injection` output, folded into `reasons` | N/A |

## 6. LLM judge (optional layer)

- Runs only when `ANTI_CHEAT_GUARD_ENABLED=true`, `ANTI_CHEAT_LLM_JUDGE=true`,
  and answer length ≥ 200 chars.
- Reuses the existing `get_llm_service()` seam (tests monkeypatch it today).
- One call per answer: returns a 0–100 AI-likelihood score plus short reasons.
- **Failure safety:** any exception ⇒ judge is skipped (`llm_ai_score: null`),
  `assess()` continues with heuristic signals. The guard never raises.

## 7. Scoring & decision policy

1. Heuristic signals score an answer 0–100 (`score`).
2. If the judge ran, it is blended with heuristics (weights live in
   `anti_cheat.py`, documented there).
3. Best-evidence-wins floor: the strongest single signal sets the minimum
   score, so decisive machine-typing/tamper evidence cannot be diluted (§4.6).
4. `score >= ANTI_CHEAT_FLAG_THRESHOLD` ⇒ that answer flagged; session
   aggregate = max per-answer score, `flagged` likewise.
5. Per-answer results append to `brain.integrity_signals`; `brain.integrity_score`
   holds the aggregate. Both persist with the session state (v4 store).
6. **Flags are report-only while below the limit.** No auto-fail, no
   interruption. When `flagged_count` reaches `ANTI_CHEAT_MAX_FLAGS`, the
   session terminates after a fair evaluation (§4.5) and the report carries
   `integrity_terminated` with a reason.

## 8. Testing matrix

| Case | Expectation |
|---|---|
| Guard disabled (default) | `assess()` pass-through; **zero** LLM calls; state untouched |
| Heuristic math | latency, duplicate_ratio, fingerprint values correct on crafted inputs |
| Threshold | correct `flagged` per answer and aggregate at boundary |
| Cadence superhuman | sustained > 8 cps intervals ⇒ cadence 92, flagged |
| Cadence transcription | bursts + recurring look-up pauses ⇒ cadence 55–72, flagged at 72 |
| Human cadence | variable rhythm ⇒ not flagged |
| Pointer leaves / tamper gaps | ≥ threshold counts ⇒ flagged with reasons |
| Voice answers | cadence/paste/typing signals skipped even if client forwards them |
| LLM judge success | stubbed via `get_llm_service` monkeypatch; blend applied |
| LLM judge failure | skipped, `llm_ai_score: null`, guard still returns, no raise |
| Engine flow with guard on | a full answer turn completes with stubbed judge + enabled guard |
| Missing client telemetry | backend behaves identically (no paste/focus signals, no error) |

## 9. Out of scope / future tiers

Not implemented (invasive and legally risky for v1; the timing + text + paste +
tab-switch + cadence + pointer + tamper + time-box stack covers the realistic
AI-cheating paths):

- Camera / eye-tracking proctoring, audio analysis (a second human whispering
  is only catchable by webcam/audio proctoring — deliberately deferred)
- Cross-candidate answer similarity (needs embeddings infra — Pinecone is
  available if desired later)
- Lockdown browser / second-display blocking (VM-level; beyond a web page)

## 10. Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-13 | Contract drafted; spec frozen for implementation |
| 1.1 | 2026-08-14 | Hardening: cadence/pointer/tamper signals (§4.6), answer time-box (§4.7), best-evidence-wins scoring, flag-limit termination policy (§4.5), new env vars, policy fields, report signal fields |