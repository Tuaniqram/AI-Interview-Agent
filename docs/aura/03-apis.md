# 03 — APIs used by the interview flow

> Last updated: 2026-08-09 · Tag: [AURA-1.3][T4-calibration-ranking]
> Scope: only the endpoints the interview flow (demo autopilot / demo page) actually exercises.

Base URL: `http://localhost:8000`. WS base: `ws://<host>/ws/...`.

## REST endpoints

| # | Method | Path | Auth | Purpose | Source |
|---|---|---|---|---|---|
| 1 | POST | `/api/v1/auth/login` | — | Org login → `tokens.access_token` + `memberships` | `app/api/v1/auth.py` |
| 2 | GET | `/api/v1/departments` | org token + `X-Org-Id` | First department for the role | `app/api/v1/departments.py` |
| 3 | GET | `/api/v1/marketplace/org/{org_id}/interviews` | org token | Reuse existing listing | `app/api/v1/marketplace.py` |
| 4 | POST | `/api/v1/marketplace/interviews` | org owner | Create a public listing (only when none exists) | `app/api/v1/marketplace.py` |
| 5 | POST | `/api/v1/candidates/login` | — | Candidate login → `tokens.access_token` | `app/api/v1/candidates.py` |
| 6 | POST | `/api/v1/candidates/register` | — | First-time candidate registration | `app/api/v1/candidates.py` |
| 7 | GET | `/api/v1/candidates/me` | candidate token | Candidate name/profile | `app/api/v1/candidates.py` |
| 8 | POST | `/api/v1/marketplace/interviews/{interview_id}/start` | — | Creates the interview session → `session_id` | `app/api/v1/marketplace.py:55` |
| 9 | GET | `/interviews/{session_id}/summary` | candidate token | Transcript + v4 verdict/composite | `app/api/interview_agent.py` |
| 10 | GET | `/api/v1/intelligence/brain/{session_id}` | candidate token | Assembled brain + evidence graph + timeline | `app/api/v1/intelligence.py:124` (`get_brain`) |

### Endpoint details

**8. POST `/api/v1/marketplace/interviews/{id}/start`**
Body: `{"candidate_email": "...", "candidate_name": "..."}` → `{session_id, ...}`.
Creates the `interview_sessions` row + links candidate.

**9. GET `/interviews/{sid}/summary`**
Returns `v4_verdict`, `v4_confidence`, `v4_composite_score`, `v4_evidence_count`,
`v4_questions_asked`, `v4_hypothesis_outcomes`, `v4_competency_summary`
(per-comp `average_score` / `evidence_count` / `gap`).

**10. GET `/api/v1/intelligence/brain/{sid}`** — the "brain view" output
(sample captured at `D:\UnityTemp\opencode\aura-run\brain_view.json`).
Response shape:
```
{
  "session_id": ...,
  "interview_brain": { ...brain-layer fields... },
  "evidence_graph":  { nodes, edges },
  "timeline":        [ ...event entries... ]
}
```
The bundle **build** (`build_interview_intelligence`) fires from
`app/engine/lifecycle.py`, not from this GET — this endpoint only assembles/reads.

## T4 org-side endpoints (beyond the core interview flow)

Calibration loop + ranking run on the org side (not part of the autopilot flow).
All require an org owner/member token.

### Calibration loop — `app/api/v1/calibration.py`

| # | Method | Path | Purpose |
|---|---|---|---|
| 11 | PUT | `/api/v1/orgs/{org_id}/calibration/feedback/{session_id}` | Record post-hire `actual_outcome` (strong_performance / met_expectations / below_expectations / terminated_during_probation / no_feedback) against a completed session; snapshots predicted verdict/score/difficulty/floor into `calibration_feedback` |
| 12 | GET | `/api/v1/orgs/{org_id}/calibration/drift` | Predicted-vs-actual reconciliation — overall, by family, by difficulty-credit band, correctness rate, over/under-prediction counts, deterministic insight strings |
| 13 | GET | `/api/v1/orgs/{org_id}/calibration/drift/summary` | Headline numbers: tracked, awaiting feedback, matched, correct, over/under |

### Ranking — `app/api/v1/candidate_ranking.py`

`GET /api/v1/orgs/{org_id}/candidates/ranking` now returns, per row:
`rank`, `final_score`, `weighted_score`, **`calibrated_score`** (null when the
session has no persisted `calibration_state`), **`difficulty_reached`**,
**`role_floor`**, **`family`**, **`score_band`**, **`comparable_note`** (set
when the candidate's family differs from the cohort's dominant family). New
query params: `sort_by=final|calibrated` (default `final`, nulls last) and
`family` (filter to a detected family, e.g. `marketing`). `/ranking/summary`
and `/export` are unchanged.

## WebSocket — `/ws/interview/{session_id}?token=<candidate_jwt>`

Handler: `app/api/interview_ws.py:297` (`interview_websocket`). Candidate identity
resolves from the `token` query param. On connect the server sends
`{type: "connected", session_id}`.

### Client → server messages

| type | payload | behavior |
|---|---|---|
| `ping` | `{}` | replies `pong` |
| `start_interview` | `{session_id}` | builds state (resolve_competencies → role context → company brain) and runs `engine.start_session`; emits `question` |
| `request_question` | `{session_id}` | re-emits the current question from store |
| `submit_answer` | `{candidate_answer}` | `engine.process_answer`; emits `status/evaluating` then `evaluation` or `report` |
| `get_status` | `{session_id}` | emits `status_snapshot` |

### Server → client frames

| type | contents |
|---|---|
| `connected` | `{session_id}` |
| `pong` | echo of ping id |
| `question` | start response: question, phase, difficulty, question_number, conversation turn |
| `status` | phase transitions (`evaluating`, `question_ready`, …) |
| `evaluation` | per-answer result: evaluation + next question info + `brain` (assembled layers: `brain_utilization`, `evidence_cursor`, `calibration_state`, `difficulty_state`, `candidate_memory`) |
| `report` | final report (session complete) |
| `status_snapshot` | `get_status` result |
| `error` | `{detail}` |

Every client frame is echoed with an `id`; the server wraps responses via
`_send_id`. Frame loop is a single `while True` reading `receive_text()` with a
60s idle timeout.
