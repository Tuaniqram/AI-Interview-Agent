# AURA V4 → V5/V6/Enterprise — Architecture Upgrade Strategy

*Grounded in the actual V4 codebase (FastAPI + WS engine, imperative pipeline, dual-backend `V4SessionStore` (memory | Redis), Supabase Postgres, Pinecone, React).*

**Key assumptions:** target ≈ 1,000–5,000 concurrent interviews initially; single-region cloud first; Python backend stays; the "engine controls the interview" philosophy is non-negotiable; existing DB schema (orgs, candidates, sessions, messages, evaluations, evidence) is retained and extended, not replaced.

---

## 1. Architecture Review

### Already strong (keep as-is)

| Strength | Where | Why it matters |
|---|---|---|
| Imperative pipeline | `interview_v4.py:71 process_v4_answer` | Deterministic, unit-testable (88 tests pass), no framework lock-in |
| Evidence-driven core | `evidence_extractor_node` + `competency_summary` | Explainability by construction — every score traces to evidence |
| Rule-based reflection | `reflection_engine.py` | Contradiction/sufficiency/verdict logic is auditable and testable |
| Hypothesis lifecycle | `hypothesis_manager.py` | untested → testing → confirmed/refuted with entropy-based (EIG) targeting |
| Prompt-as-config | `prompts/*.md` + `prompt_loader.py` | Tuning intelligence without code deploys; foundation for tenant override |
| Style system | `interview_styles.py` | Already a seed of "configurable interview behavior" |
| Write-back per turn | `_persist_answer_turn` + `store.checkpoint()` | Every answer produces a DB audit trail + durable checkpoint (bumps `state_version`) |
| Pipeline observability | `EventLog.append()` | 10 event types at every pipeline stage (interview_events, best-effort) |
| WS protocol shape | `interview_ws.py:189` | connected/question/status/evaluation/report with `_id` echo — extensible |
| Injection guard | `input_sanitizer.py` | Correct instinct; needs hardening, not replacement |

### What should NOT change
- The 7-node start pipeline and 4-node answer pipeline **order and responsibility split**.
- Deterministic routing (probe / change_competency / finish). LLM never decides the route.
- Evidence → competency summary → reflection loop as the assessment core.
- Prompt-file templating model.
- The WebSocket message vocabulary.

### Current weaknesses (in priority order)
1. **State is process-local** (`v4_session_store.py`). One replica only; restart loses live interviews; no resume; no horizontal scale. *This is the #1 blocker for everything else.*
2. **LLM calls inline in the request path.** Start latency already has a 15s RAG timeout (`company_context_node`); answer loop serializes evaluation→governor→generation. No streaming, no retry, no queue.
3. **No observability of decisions.** No spans, no prompt-version/input snapshots, no per-call cost tracking. "Why did it score 6.2?" is currently unanswerable post-hoc.
4. **Raw LLM scores with no calibration** — no rubric anchoring, no bias checks, no uncertainty handling.
5. **RAG is single-purpose.** Only department docs, one query per start, no tenant-level isolation story, no rerank/caching.
6. **No long-term candidate memory** — candidate_profile is a snapshot; cross-interview growth is invisible.
7. **No background workers** — evidence persistence and report work run inline in the WS handler.
8. **Multi-tenancy is partial** — orgs exist, but styles/competencies/prompts/scoring rules are effectively global (only AURA style; global taxonomy with scorecard overrides).
9. **Single LLM provider coupling** in `llm_service.py` — no fallback, no model routing, no cost governance.
10. **No retry/idempotency** on `submit_answer` — a dropped WS message can double-evaluate.

### Future architecture (layer view)

```
┌────────────────────────────────────────────────────────────────┐
│ API LAYER          REST (session mgmt, admin, reports)          │
│                    WS gateway (interview runtime)               │
│                    HTTP streaming (fallback for non-WS clients) │
├────────────────────────────────────────────────────────────────┤
│ INTERVIEW RUNTIME  Engine orchestrator (state machine)          │
│                    node runner: timeout/retry/checkpoint        │
│                    event log writer (audit + replay)            │
├────────────────────────────────────────────────────────────────┤
│ STATE LAYER        Redis (hot per-session state)                │
│                    Postgres JSONB (durable checkpoints)         │
│                    Append-only interview event log              │
├────────────────────────────────────────────────────────────────┤
│ AI COGNITIVE LAYER Cognitive components (unchanged philosophy)  │
│                    LLM gateway: providers, models, cost, cache  │
│                    Prompt registry (tenant-versioned)           │
├────────────────────────────────────────────────────────────────┤
│ KNOWLEDGE LAYER    Vector store (tenant-isolated) + BM25        │
│                    Reranker + metadata filtering + cache        │
├────────────────────────────────────────────────────────────────┤
│ EVALUATION INTELL. Calibration, bias audit, evidence QA,        │
│                    uncertainty/abstention, adjudication         │
├────────────────────────────────────────────────────────────────┤
│ ANALYTICS LAYER    Event stream → reports, trends, org insights │
├────────────────────────────────────────────────────────────────┤
│ PERSISTENCE LAYER  Postgres (relational + JSONB), object store  │
│                    (documents), vector store, message queue     │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. Orchestration Decision

| Criterion | A. Stay imperative | B. LangGraph | C. Custom engine | D. Hybrid (imperative + thin engine) |
|---|---|---|---|---|
| Scalability | ❌ State stays in-process unless rebuilt anyway | ➖ Graph adds nothing; state problem unchanged | ✅ Engine owns state persistence | ✅ Engine owns it |
| Debugging | ✅ Excellent today | ❌ LangGraph middleware layers obfuscate | ✅ Event log = replay | ✅ Event log = replay |
| Reliability | ❌ No retry/timeout/checkpoint built-in | ➖ Adds its own failure modes | ✅ Node contracts: timeout/retry/idempotency | ✅ Same |
| Observability | ❌ Manual | ➖ Built-in tracing, but generic | ✅ Event log is *decision* audit | ✅ Same |
| Maintenance | ✅ 10 nodes, trivial | ❌ New framework + DSL for 3 routes | ✅ ~1–2k LOC, all yours | ✅ Same |
| Complexity | ✅ Zero | ❌ High | ➖ Medium | ➖ Medium |
| Philosophy fit | ✅ | ❌ Graph pushes routing into framework | ✅ | ✅ |

**Recommendation: D — stay imperative, add a thin custom workflow engine.**

Rationale:
- The pipeline is **10 nodes and 3 branches**. LangGraph solves multi-agent/highly-branching problems; AURA is neither. Adding it buys a graph DSL and checkpointing we'd have to fight, and it displaces the engine's control philosophy.
- The real problems (durability, retry, audit) are solved by an **event-sourced runner**: each node implements a contract (`run(state, ctx) -> state_delta`), the runner wraps it with timeout, retry-on-transient-LLM-error, and writes every transition to the event log. That's ~1–2k LOC, fully testable, zero framework risk.
- Keep the existing node functions **untouched** (they already satisfy the contract shape: `(state) -> state`). This is a *wrapping* change, not a rewrite — migration risk is low.

---

## 3. State Management Upgrade

### Comparison

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Redis only | Fast, TTL, cross-replica | No durability guarantee; audit needs another store anyway | Part of the answer |
| Postgres JSONB only | Durable, queryable, transactional | Slow for hot loops (every turn writes); no TTL | Checkpoints only |
| Full event sourcing | Perfect audit/replay, explains every decision | Build cost; replay logic; overkill as *primary* runtime state | Use for the event log, not as the state store |
| Hybrid cache | Hot path fast + durable + auditable | Two writes per turn | **Recommended** |

### Recommended design

**Tier 1 — Hot runtime state (Redis):** `aura:session:{id}` hash, TTL = session max duration + grace. Write on every node completion. This replaces `v4_session_store` transparently (same `get/set/get_or_raise` API — swap the backend behind the existing interface).

**Tier 2 — Durable checkpoints (Postgres JSONB):** snapshot written on answer completion and completion — exactly where `_persist_answer_turn`/`_persist_completion` already fire. Enables resume-after-restart and cross-replica pickup.

**Tier 3 — Event log (append-only):** `interview_events(id, session_id, seq, event_type, payload, ts)` written *before* each state mutation (Outbox pattern). Events: `question_asked`, `answer_received`, `evaluation_done`, `evidence_added`, `difficulty_changed`, `action_decided`, `question_selected`, `hypothesis_updated`, `interview_finished`. This is the audit trail, the replay source, and the "why" database (see §12).

**Conversation memory** stays in `messages` (already relational, already written per turn).
**Candidate memory / company memory** are new tables (§8, §7).

---

## 4. Enterprise Multi-Tenant Architecture

### Config bundle per tenant (inheritance chain: global → org → template → session)

| Knob | Today | V5 design |
|---|---|---|
| Interview style | Global (`get_style`) | `org_styles` table; org can clone/edit AURA |
| Competency model | Global taxonomy + scorecard | `org_competency_models` (weights, custom competencies, min_evidence per competency) |
| Scoring rules | Hardcoded | `org_rubrics` (dimension weights, verdict thresholds, score anchors) |
| Evaluation criteria | Same for all | Rubric-scoped evaluator prompt rendering |
| Prompts | Global .md | Prompt registry: `prompt_slots(tenant_id, slot, version, content, active)` — rendered with tenant context |
| Hiring standards | Global verdict logic | `org_hiring_policies` (thresholds per org, human-review gate per role) |

### Database architecture
- Add `org_id` to every interview-adjacent table (evidence, evaluations, prompts, styles). Enforce via **Postgres Row-Level Security** + an org-scoped DB role for the app; never trust app-level filtering alone.
- Vector isolation: namespace-per-tenant + mandatory `org_id` metadata filter at query time (§7).
- Prompt resolution: `tenant prompt → template prompt → global default`, resolved once per session start and cached by version hash.
- The engine code stays **tenant-agnostic** — all differences arrive as *data* (style, rubric, prompts, policy). This is the single most important V5 architectural rule: *tenant behavior is configuration, never code branches.*

---

## 5. AI Cognitive Layer Upgrade

| Agent | Should exist? | Why | Benefit | Complexity | Priority |
|---|---|---|---|---|---|
| **Interview Planner** | Yes (V6) | Evolves strategy_brain + competency_planner into a multi-turn plan ("next 3 questions, which competencies, what evidence is missing") | Fewer redundant questions, shorter interviews, better coverage | Medium | P1 (V6) |
| **Calibration Agent** | Yes (V6) | Anchors LLM scores to rubric exemplars + org's historical score distribution | Scores become comparable across candidates/orgs — prerequisite for hiring decisions | Medium-High | P1 (V6) |
| **Bias Detection Agent** | Yes (V6) | Post-hoc audit: flag correlations between scores and protected attributes, lexical/style biases | Legal defensibility; org trust | Medium | P2 (V6) |
| **Evidence Validation Agent** | Yes (V6) | Every score must cite grounded evidence; rejects ungrounded LLM claims | Kills hallucinated evaluations at the source | Medium | P1 (V6) |
| **Candidate Memory Agent** | Yes (V6) | Synthesizes long-term competency trajectory (§8) | Re-interviews become "growth assessment", not cold starts | Medium | P2 (V6) |
| **Hiring Decision Agent** | Yes (V7) | Adjudicates verdict from evidence + org policy with explicit reasoning; never the sole decider | Explainable, appealable hiring decisions | High | P3 (V7) |
| **Research Agent** | Optional (V7) | Enriches role/company context from public sources | Better questions for niche roles | High | P4 — defer |

Rule: **new agents are advisory or post-hoc by default.** Only planner/validation touch the live pipeline; everything else runs asynchronously or on report generation so they can't slow down or corrupt live interviews.

---

## 6. Evaluation Intelligence Upgrade

- **Score calibration:** rubric-anchored exemplars in prompts; per-org calibration set of scored answers; post-hoc monotonic mapping (LLM score → calibrated score) fitted from human scores; store `raw_score` + `calibrated_score` separately in evaluations.
- **Confidence:** existing per-dimension confidence becomes *calibrated uncertainty* — derive from LLM logprobs + cross-mode agreement (run 1 unified + parallel spot-checks on a sample); low confidence → **abstain policy**: reflection engine emits `needs_more_evidence` instead of scoring the dimension.
- **Evidence quality scoring:** each evidence item gets `relevance`, `specificity`, `grounding` (quote-match) scores — surface in report; used to weight competency summary (evidence_count alone is too naive).
- **Hallucination prevention:** structural — evidence must reference a verbatim span of the answer (similarity check); ungrounded dimension scores are downgraded; the Evidence Validation Agent (§5) automates this in V6.
- **Bias reduction:** blind evaluation during scoring (strip name/school/company names from the evaluated text); bias audit report per org/role; never use candidate memory in *scoring* prompts (only in planning/hypothesis) to avoid anchoring.
- **Human alignment:** calibration sessions where org reviews N reports; their feedback tunes rubrics + verdict thresholds; expose "human vs engine agreement" analytics.

---

## 7. RAG / Knowledge Architecture Upgrade

### Sources (V5 → V6)
1. Company knowledge (docs) — *exists*
2. Job descriptions — *exists* (listing descriptions)
3. Interview rubrics / scoring guides — new: per-tenant rubric docs fed to evaluator rendering
4. Engineering standards — new: org standards docs for technical grounding
5. Historical hiring decisions (anonymized) — new (V6): "similar past candidates scored X" for planning
6. Candidate history — new (V6): via Candidate Memory, **retrieval-only, never scoring**

### Retrieval strategy
- **Hybrid retrieval:** dense (vector) + BM25 sparse, merged with RRF, then a **cross-encoder rerank** (top-5). This is the biggest single quality lever on RAG.
- **Query augmentation:** expand the phase-aware query templates (already exists) with tenant job_role + weak skills (already exists) + rubric terms.
- **Caching:** retrieved context is cached per (tenant, department, phase, job_role) — today's 15s cold-start RAG should be ~50ms cached.
- **Filtering:** mandatory metadata filters — `tenant_id`, `department_id`, `doc_type`, `is_public`, `vintage`.

### Vector DB design
- Keep Pinecone (working today) but enforce **namespace = tenant** + metadata filter as defense-in-depth; add `pgvector` for small, hot collections (rubrics, policies) co-located with Postgres. If ops burden grows, consolidate on pgvector — tradeoff noted, not forced.
- Indexing pipeline: document upload → chunk (fixed ~500 tok, 15% overlap, section-aware) → embed → write vector + `documents`/`chunks` rows in Postgres → mark ready. Runs in a **background worker** (today embedding is inline and untracked).

---

## 8. Candidate Intelligence Memory

### Storage
- `candidate_memory(candidate_id, interview_id, competency_id, direction)` — append-only observations, one row per competency per interview: `{trend: improved|declined|stable, score, evidence_refs, summary}`.
- `candidate_memory_summary(candidate_id, updated_at, JSONB)` — materialized synthesis per competency (count, trend, latest evidence ids, confidence) rebuilt after each completed interview.
- Never store raw audio/video; transcripts retained under consent + retention policy.

### Retrieval & use
- **Planning only:** candidate memory is injected into strategy_brain + hypothesis generation as a "Prior" block ("Candidate previously weak in system design — prioritize probing with growth framing").
- **Explicitly excluded from evaluation prompts** (anchoring/bias).
- Report can include a "Growth since last interview" section (V6).

### Privacy
- Consent record per candidate; right-to-erase cascades to memory + evidence references (anonymize or delete per policy); retention TTL configurable per tenant; memory summaries never include PII beyond what the candidate provided.

---

## 9. Real-Time Interview Experience Upgrade

- **Streaming:** pipeline already sends `status` pushes; add per-node progress events (`stage: evaluating|governing|reflecting`) and stream the *next question* tokens for perceived latency. Node execution moves off the WS handler into a worker owned by the session (WebSocket becomes a thin projector of state — this also fixes replica affinity).
- **Voice (V6):** streaming STT (third-party, e.g., Deepgram/AssemblyAI) → normalized transcript → `submit_answer`. TTS for AURA voice. **Adapters, not engine changes** — the engine consumes text.
- **Avatar (V7/Enterprise):** the removed `v3/app/speech` stack gets rebuilt as a *streaming TTS microservice* if a paid tier demands it; default remains browser-native SpeechSynthesis (current frontend behavior).
- **Speech analysis (V7):** prosody/pace/filler metrics as auxiliary, non-scoring signals shown to interviewers.
- **Interruptions:** WS already bidirectional — add `interrupt` message (stop TTS/streaming), `turn_id` on submissions for idempotent answer acceptance (server dedupes by turn_id).
- **Latency budget:** strategy_brain cached (`strategy_cache_valid` already exists) → first question pre-generated during session creation (parallel with WS connect) → evaluation dims parallelized in unified mode (already supported in parallel mode) → all persistence moves to background workers with Outbox.

---

## 10. Production Infrastructure

| Layer | Choice | Notes |
|---|---|---|
| Containers | Docker multi-stage; dev via docker-compose | — |
| Orchestration | Managed first (Railway/Render/Fly), **K8s at >2–3k concurrent** | Don't pay K8s tax early |
| Runtime state | Redis (managed) | Hot state + rate limits + pub/sub |
| DB | Supabase Postgres (current) → dedicated managed Postgres + PgBouncer when >~50k sessions/mo | RLS stays either way |
| Queue | **Redis Streams + consumer groups** (no new broker) | Workers: evidence persistence, report gen, RAG indexing, email, analytics |
| Workers | Separate deployment unit, scale independently | Same image, `WORKER=true` env |
| API | Stateless replicas behind LB | Session routing via Redis, not stickiness |
| WS | Replica-safe once state is in Redis | Any node can serve any session |
| Monitoring | Prometheus + Grafana | HTTP/WS/queue/LLM latency dashboards |
| Logging | Structured JSON logs → Loki/CloudWatch | Node-level logs with session_id + trace_id |
| Tracing | **OpenTelemetry** (FastAPI + Redis + LLM gateway spans) | This is non-negotiable for V5 |
| Secrets | Vault/KMS; no secrets in env files | `SECRET_KEY` warning in logs is a 1-day fix |

---

## 11. Security Architecture

- **Prompt injection:** current detection stays as a *first* gate; structural defenses become primary — candidate input is never concatenated into the instruction region, it is passed as a delimited data field; output schema validation on every LLM call; injection attempts logged and surfaced to interviewer; rate-limit repeat offenders per tenant.
- **Malicious documents:** upload → type/size allowlist → scan (ClamAV or managed scan) → text extraction in an **isolated worker** → embedding; store original in private object storage.
- **Tenant isolation:** `org_id` on all tables + **Postgres RLS**; vector namespaces; tenant-scoped API rate limits; per-tenant keys (KMS) for enterprise tier.
- **Auth/authz:** JWT (exists) + rotation; refresh-token reuse detection; MFA for org admins; candidate tokens scoped per session (already `token` in WS URL — keep, add expiry); RBAC extended to report/evidence/admin scopes.
- **Candidate privacy:** PII minimization in prompts (evaluator receives *answers*, not identity), retention policies, consent registry, right-to-erase (§8).
- **Encryption:** TLS everywhere; AES-256 at rest; secrets via Vault; audit of every admin/data access via existing `audit_logs` (extend coverage to evidence/report reads).

---

## 12. Observability System

**Core concept — the interview is a trace:**
- Every interview gets a `trace_id`; every node execution a span: `node, prompt_version, model, input_snapshot (truncated), output, duration_ms, tokens, cost, decision`.
- The **event log (§3) is the "why" database**: `interview_events` already records question/answer/evaluation/action decisions. Query it to answer *any* "why": which evidence → score; which contradictions → finish; which hypothesis → question.
- **LLM cost tracking:** `model_usage(call_id, session_id, node, provider, model, prompt_version, in_tokens, out_tokens, cost, latency)` written by the LLM gateway on every call — the gateway replaces direct `llm_service` calls.
- **Dashboards:** p50/p95/p99 latency per node; token/cost per session and per tenant; failure rate per node; injection attempt rate; hallucination/abstention rate.
- **Failure debugging:** replay tool — reconstruct any session's state from event log (replay events → rebuild state → re-run node in isolation).
- **Explanation API (V6):** `GET /interviews/{id}/explain` — synthesize "why this score/verdict" from the event log; powers org review UI.

---

## 13. Database Redesign

*Extend, don't rebuild. Existing: `organizations`, `users`, `org_users`, `departments`, `candidates`, `interview_sessions`, `messages`, `evaluations`, `interview_evidence`, `scorecard_templates`, `interview_templates`, `public_interviews`, `audit_logs`.*

| Domain | New/Changed tables | Notes |
|---|---|---|
| Tenancy | `org_styles`, `org_competency_models`, `org_rubrics`, `org_hiring_policies`, `prompt_slots(tenant_id, slot, version, content, active)` | All config; engine reads resolved bundles |
| Runtime | `interview_events` (event log, append-only) | Audit + replay + "why" |
| | `interview_snapshots(session_id, state JSONB, created_at)` | Checkpoints; resume + replica pickup |
| Competencies | `competency_models` (global), `org_competency_models` (weights/min_evidence) | Replaces hardcoded taxonomy assumptions |
| Evidence | `evidence_quality` on `interview_evidence` (relevance/specificity/grounding) | Weighting (§6) |
| Evaluations | `evaluation_dimension_scores` (dim, raw_score, calibrated_score, confidence, abstained) | Keeps `evaluations` summary row |
| | `calibration_sets` (exemplar answers + human scores) | Per tenant/rubric |
| Candidate memory | `candidate_memory` (append-only), `candidate_memory_summary` (JSONB), `candidate_consent` | §8 |
| Knowledge | `documents`, `chunks` (+ vector store sidecar), `retrieval_logs` | Indexing provenance |
| Prompts | `prompt_slots` + `prompt_versions` | Version-pinned rendering |
| Model usage | `model_usage` (per call) | Cost + latency + reliability metrics |
| Sessions | add `resume_token`, `state_version` to `interview_sessions` | Concurrency control on WS |

---

## 14. Version Roadmap

### AURA V5 — Production Foundation (priority: correctness of state & ops)
| Feature | Priority | Difficulty | Impact |
|---|---|---|---|
| Redis-backed session store behind existing interface | P0 | Low | Unblocks scaling + resume |
| Interview event log + checkpoints | P0 | Medium | Audit + replay + "why" |
| LLM gateway (models, cost tracking, retries, fallback) | P0 | Medium | Cost control + reliability |
| OTel tracing + structured logs | P0 | Low-Med | Debugging |
| Background workers (persistence, indexing, email) | P0 | Medium | WS handler slimmed |
| WS replica-safety (state in Redis, worker-owned pipeline) | P1 | High | Horizontal scale |
| Tenant config bundles + RLS | P1 | Medium | Multi-tenant readiness |
| Prompt registry (tenant-versioned) | P1 | Medium | Per-org behavior |
| Retry/idempotency (turn_id) + rate limits | P1 | Low-Med | Robustness |
| Hybrid retrieval + rerank + RAG cache | P1 | Medium | Question quality + latency |

### AURA V6 — Advanced Intelligence Layer
| Feature | Priority | Difficulty | Impact |
|---|---|---|---|
| Evaluation calibration + abstention | P0 | High | Trustworthy scores |
| Evidence validation agent | P0 | Medium | Kills hallucinated scores |
| Bias detection audit | P1 | High | Legal defensibility |
| Candidate memory | P1 | Medium | Growth assessment |
| Interview planner (multi-turn) | P1 | High | Interview quality |
| Information Gain Engine (probabilistic question selection, §15.2) | P1 | Medium | Question quality + "why this question" *(implemented — Phase 2)* |
| Explanation API | P1 | Medium | Org trust/review |
| Historical decision retrieval | P2 | High | Planning quality |

### AURA V7 / Enterprise — Large-Scale SaaS
- Hiring decision agent with human-review workflow & appeals
- Voice interviews (STT adapter) + speech analytics; avatar tier
- Org analytics product (score trends, calibration dashboards, bias reports)
- SSO/SCIM, MFA, audit/compliance exports, data residency options
- Marketplace of interview styles/competency models (cross-tenant, vetted)
- High availability (multi-AZ), regional failover

---

## 15. External Architecture Review — Mapping & Response

*Source: ChatGPT "AURA Engine Architecture Review" (https://chatgpt.com/share/6a721056-1e08-83ec-9fbd-0ee8abe5c48b), score 9.3/10. Reviewed against the actual codebase — many proposals already exist; see §15.1 before building anything.*

### 15.1 Review proposals vs. current code

| Review proposal | Status | Where / note |
|---|---|---|
| Interview Memory Engine (observations, patterns, risk, behavior timelines) | Already exists | `observations` model (`db.py:937`) with `type/value/evidence/pattern/risk_signal`; `interview_events` (Phase 1) is the timeline |
| Contradictions | Already exists | `_detect_contradictions` (`reflection_engine.py:91-106`), severity-graded |
| Consistency checks | Already exists | `consistency_checks[]` per dimension (`reflection_engine.py:81-89`) |
| Coverage-weighted sufficiency | Already exists | `evidence_sufficiency.coverage_ratio` weighted by competency weights (`reflection_engine.py:144-168`) |
| Hiring formula | Already exists | `hiring_recommendation`: verdict + confidence + composite + coverage (`reflection_engine.py:192-203`) |
| Interview Timeline | Already exists | 8 event types from Phase 1 (replayable "why" DB) |
| Company Brain (RAG for all nodes) | Partial | `department_context` RAG feeds the start pipeline only |
| Dynamic Strategy Brain | Partial | `strategy_brain` runs once, cached (`strategy_cache_valid`) |
| Bayesian hypotheses | Partial — implemented | `confidence` is now a true posterior (prior `PRIOR_CONFIDENCE = 0.5`, evidence-updated each turn); remaining: context-derived prior (job_role/strategy) + calibrated evidence strength |
| **Information Gain Engine** | **Implemented (Phase 2)** | `next_target` (`hypothesis_manager.py:200`) scores by expected information gain; `_decide_next_action` (`reflection_engine.py:208-230`) unchanged — routing stays rule-based |
| Living CandidateModel | Gap (V6) | `candidate_profile` is a snapshot; no cross-interview trait evolution |
| Trust Engine (hedging/hallucination) | Gap (V6) | overlaps §6 Evidence Validation + bias audit |
| Evidence Graph | Gap (V6) | evidence→hypothesis links exist; no graph traversal for planning |
| Multidimensional difficulty | Gap | single `difficulty_level` |
| Hierarchical evaluation | Gap (V7) | flat 6-dimension evaluation |
| Multi-agent / event bus | Rejected | conflicts with V4 decision D (imperative pipeline + thin event log, §2); event log already provides audit/replay |

### 15.2 Phase 2 recommendation — Information Gain Engine (probabilistic question selection)

The review's top two ideas (**Interview Brain** + **Information Gain Engine**) collapse into one self-contained upgrade: **make question selection probabilistic**. It slots directly on top of the existing evidence→hypothesis machinery and requires no new infrastructure.

1. **Posterior per hypothesis:** replace status-only `confidence` with a light prior→posterior update. Prior from pre-interview context (job role, strategy_brain); on each evidence item update `P(confirm | evidence)` via a calibrated strength score (0..1). Keep the discrete statuses (untested/testing/confirmed/refuted) as a **derived read model** so no existing consumer breaks.
2. **Expected information gain (EIG):** for each actionable competency/dimension, score candidate questions as `EIG = H_prior − E[H_posterior]` over hypothesis posteriors. `next_target` becomes the argmax, with "untested first" kept only as a coverage tiebreak.
3. **Multidimensional difficulty (optional slice):** per-dimension `difficulty` on the probe so EIG can trade coverage vs. depth vs. differentiation.
4. **Events:** new `interview_events` types `hypothesis_updated` (before/after posterior) and `question_selected` (reason = EIG score). Same best-effort pattern.
5. **Tests:** pure-function EIG scoring + posterior update (no LLM), mirroring the Redis-store stub pattern. Deterministic, no new deps.

Cost/benefit: preserves "deterministic routing" (LLM never decides the route — it only supplies evidence strength), strictly improves question quality, and yields "why this question" explainability for free (the EIG score itself).

**Status: implemented (Phase 2).** `expected_information_gain` + entropy-based `next_target` in `hypothesis_manager.py` (initial prior `PRIOR_CONFIDENCE = 0.5`, `information_gain`/`selection_reason` on `hypothesis_target`, legacy deep-probe fallback retained); `hypothesis_updated` (before/after) and `question_selected` events wired into `interview_v4.py` answer path and `interview_ws.py` start path; 14 pure-function tests in `tests/test_hypothesis_information_gain.py` (suite now 88 green). The double `hypothesis_node` run in the `change_competency` path was also removed (latent double-evidence-update bug).

---

## FINAL OUTPUT

### 1. Final AURA Enterprise architecture

```
                      ┌──────────────────────────────────────────────┐
  React Frontend      │              API / Gateway Layer              │
                      │  REST: sessions, reports, admin, config       │
                      │  WS:   /ws/interview/{id} (thin projector)    │
                      │  HTTP streaming fallback                      │
                      └───────┬──────────────────┬────────────────────┘
                              │                  │
        ┌─────────────────────▼────┐   ┌─────────▼──────────────────┐
        │    Interview Runtime      │   │   Queue (Redis Streams)    │
        │    Engine Orchestrator    │   │   workers: persistence,    │
        │  - node runner (timeout,  │   │   report, indexing, email  │
        │    retry, checkpoint)     │   └─────────┬──────────────────┘
        │  - event log writer       │             │
        └──────┬──────────┬─────────┘             │
               │          │                       │
        ┌──────▼───┐ ┌────▼──────┐   ┌────────────▼───────────────┐
        │  Redis   │ │  Postgres │   │  LLM Gateway                │
        │ hot state│ │ - config  │   │  - providers/fallback       │
        │ rate/cache││ - sessions│   │  - cost & usage tracking    │
        │          │ │ - evidence│   │  - output schema validation │
        │          │ │ - events  │   └────────────┬────────────────┘
        │          │ │ - memory  │                │
        └──────────┘ └────┬──────┘   ┌────────────▼────────────────┐
                          │          │  AI Cognitive Layer          │
                 ┌────────▼─────┐    │  planner→strategy→hypothesis │
                 │ Vector + BM25│    │  →question→evaluate→validate │
                 │ - tenant ns  │    │  →evidence→govern→reflect→   │
                 │ - reranker   │    │  synthesize (V5=V4 pipeline, │
                 │ - RAG cache  │    │  V6 adds agents)             │
                 └──────────────┘    └────────────┬────────────────┘
                                                  │
                             ┌────────────────────▼─────────────────┐
                             │  Observability: OTel → Tempo/Loki/    │
                             │  Prometheus; decision traces; cost    │
                             └──────────────────────────────────────┘
```

### 2. Migration plan from V4 (6 phases, each independently shippable)
1. **State swap:** replace `v4_session_store` backend with Redis behind the same interface; add snapshot + event-log writes at existing persist points. *(No pipeline changes; zero behavior drift.)*
2. **LLM gateway + tracing:** wrap `llm_service`, add `model_usage`, OTel spans on every node. *(No behavioral change.)*
3. **Worker extraction:** move evidence persistence/report write-backs to Redis Streams consumers (Outbox at existing persist points).
4. **Tenancy:** add `org_id` + RLS, config bundle resolution, prompt registry. Engine untouched.
5. **RAG upgrade:** hybrid retrieval + rerank + cache; move indexing to worker.
6. **V6 intelligence:** calibration, evidence validation, bias audit, candidate memory, planner, explanation API — each behind feature flags.

Rules: every phase ships with tests green (current suite is the safety net); no phase changes the WS message contract; the v3 legacy engine was archived and later removed (no dual-engine support).

### 3. Implementation priority order
1. Redis state store (P0, days) → 2. Event log + checkpoints → 3. LLM gateway + OTel → 4. Workers/Outbox → 5. Idempotency + rate limits → 6. Tenant bundles + RLS → 7. Prompt registry → 8. RAG v2 → 9. Calibration + evidence validation (V6) → 10. Candidate memory → 11. Bias audit → 12. Planner → 13. Information Gain Engine (§15.2) → 14. Voice → 15. Enterprise SaaS.

### 4. Biggest technical risks
1. **Redis migration correctness** (lost sessions during swap) — mitigate with write-through checkpoint + shadow reads in phase 1.
2. **WS-to-worker pipeline handoff** — the engine must become event-driven without breaking the `_id` echo contract; highest-complexity phase.
3. **Calibration quality** — calibrated scores can be *worse* than raw if exemplar sets are bad; gate on human-agreement metrics per org.
4. **RLS rollout on existing tables** — a bad RLS policy silently drops rows; ship with policy tests + row-count audit.
5. **LLM cost explosion** with parallel evaluation + rerank + new agents — hard per-session cost budgets enforced in the gateway.
6. **Bias detection false positives** — reputational risk with orgs; ship as advisory with explanations, not alarms.

### 5. Things NOT to build
- ❌ LangGraph adoption (no justification; §2).
- ❌ Full event-sourcing as the primary state store (event log for audit, JSONB for state).
- ❌ Multi-region before multi-replica works.
- ❌ Microservices decomposition of the engine (a monolith-process with workers is right at this scale).
- ❌ In-house vector DB; in-house STT/TTS; in-house K8s platform.
- ❌ An "AI interviewer" that free-form chats or lets the LLM decide routing (kills explainability).
- ❌ Rebuilding the avatar/speech stack for free tier (archived for a reason).
- ❌ Candidate memory in *scoring* prompts (anchoring bias).
- ❌ Streaming answer analysis that delays the core loop.

### 6. Final recommendation
Ship **V5 as a state-and-ops transformation, not a feature release**: Redis-backed sessions, event log, LLM gateway, tracing, workers, tenant config bundles — all behind the existing interfaces, none changing the cognitive pipeline or the WS contract. V5 is ~60% infrastructure work and its payoff is making the engine *recoverable, scalable, and explainable*. Then layer V6 intelligence (calibration → evidence validation → bias audit → candidate memory) with feature flags, keeping every new agent advisory-by-default. The V4 cognitive architecture — engine-controlled, evidence-driven, deterministically routed — survives intact; that is precisely why it can be productionized without a rewrite.
