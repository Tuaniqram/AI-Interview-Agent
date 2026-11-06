# CLAUDE API CATALOG — AI Interview Agent

> Last updated: 2026-11-06
> Base path: `/api/v1` unless noted.
> This catalog covers mounted and unmounted routes.

## Status Legend

| Status | Meaning |
|---|---|
| `ALIGNED` | Matches the current 30-table IT-only schema |
| `ALIGNED (compat)` | Kept for frontend compatibility but uses org-level data |
| `LEGACY (410)` | Endpoint exists but returns `410 Gone` |
| `RUNTIME` | Interview runtime / WebSocket |
| `PENDING AUTH` | Works, but authentication should be hardened |
| `UNMOUNTED` | Code exists but router is not included in `app/main.py` |

## Authentication Model

| Identity | Token | Notes |
|---|---|---|
| Organization user | `Authorization: Bearer <access_token>` | Plus `X-Org-Id` for org routes |
| Candidate | `Authorization: Bearer <candidate_access_token>` | Candidate JWT |
| Admin | Organization user with `is_admin = true` | `require_admin` |
| Public | None | Marketplace/public routes |
| Optional candidate | Bearer token optional | Apply and interview summary |

Organization access is checked through `organizations.owner_user_id`. There is no `org_users` table.

## 1. Auth — `/auth`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| POST | `/register` | Public | ALIGNED | Register owner user + organization |
| POST | `/login` | Public | ALIGNED | Owner login |
| POST | `/google` | Public | ALIGNED | Google owner login |
| POST | `/refresh` | Public | ALIGNED | Refresh org token |
| POST | `/logout` | Public | ALIGNED | Revoke refresh token |
| GET | `/me` | Org user | ALIGNED | Current user + owner membership |
| POST | `/forgot-password` | Public | ALIGNED | Send reset email |
| POST | `/reset-password` | Public | ALIGNED | Reset owner password |

## 2. Organizations — `/orgs`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| POST | `""` | Org user | ALIGNED | Create organization |
| GET | `/{org_id}` | Org owner | ALIGNED | Get organization |
| PATCH | `/{org_id}` | Org owner | ALIGNED | Update organization |
| GET | `/{org_id}/members` | Org owner | ALIGNED (compat) | Returns the single owner |
| POST | `/{org_id}/members` | Org owner | LEGACY (410) | Disabled: one user per org |
| POST | `/{org_id}/members/by-email` | Org owner | LEGACY (410) | Disabled |
| PATCH | `/{org_id}/members/{member_id}` | Org owner | LEGACY (410) | Disabled |
| DELETE | `/{org_id}/members/{member_id}` | Org owner | LEGACY (410) | Disabled |
| GET | `/{org_id}/templates` | Org role | ALIGNED | List organization templates |
| POST | `/{org_id}/invite` | Org owner | LEGACY (410) | Teammate invites disabled |
| GET | `/invitations/{token}` | Public | LEGACY (410) | Org invite verification disabled |
| POST | `/invitations/{token}/accept` | Org user | LEGACY (410) | Org invite acceptance disabled |

## 3. Admin — `/admin`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `/stats` | Admin | ALIGNED | Platform stats |
| GET | `/organizations` | Admin | ALIGNED | List organizations |
| POST | `/organizations/{org_id}/toggle-suspend` | Admin | ALIGNED | Suspend/activate org |
| GET | `/users` | Admin | ALIGNED | List platform users |

## 4. Analytics — `/analytics`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `/overview` | Org role | ALIGNED | Org overview metrics |
| GET | `/scores/trend` | Org role | ALIGNED | Score trend |
| GET | `/scores/distribution` | Org role | ALIGNED | Score distribution |
| GET | `/sessions/by-department` | Org role | ALIGNED (compat) | Grouped by IT role |
| GET | `/sessions/by-role` | Org role | ALIGNED | Sessions per IT role |

## 5. Audit Logs — `/orgs/{org_id}/audit-logs`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `""` | Org role | ALIGNED | List audit entries |

## 6. Candidates — `/candidates`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| POST | `/register` | Public | ALIGNED | Candidate registration |
| POST | `/login` | Public | ALIGNED | Candidate login |
| POST | `/google` | Public | ALIGNED | Candidate Google login |
| POST | `/send-verification` | Candidate | ALIGNED | Send email verification |
| POST | `/verify` | Public | ALIGNED | Verify email |
| POST | `/refresh` | Public | ALIGNED | Refresh candidate token |
| GET | `/me` | Candidate | ALIGNED | Candidate profile |
| PATCH | `/me` | Candidate | ALIGNED | Update profile |
| GET | `/interviews` | Candidate | ALIGNED | Candidate interview history |
| GET | `/interviews/{interview_id}` | Candidate | ALIGNED | Interview detail |
| GET | `/stats` | Candidate | ALIGNED | Candidate stats |
| GET | `/competency-scores` | Candidate | ALIGNED | Competency scores |
| POST | `/saved-listings/{listing_id}` | Candidate | ALIGNED | Save listing |
| DELETE | `/saved-listings/{listing_id}` | Candidate | ALIGNED | Remove saved listing |
| GET | `/saved-listings` | Candidate | ALIGNED | List saved listings |
| POST | `/practice/start` | Candidate | ALIGNED | Start practice session |
| POST | `/forgot-password` | Public | ALIGNED | Candidate reset email |
| POST | `/reset-password` | Public | ALIGNED | Candidate password reset |
| POST | `/me/resume` | Candidate | ALIGNED | Upload resume |
| GET | `/{candidate_id}/resume` | Candidate | PENDING AUTH | Resume access; verify ownership |

## 7. Candidate Ranking — `/orgs/{org_id}/candidates`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `/ranking` | Org role | ALIGNED | Ranked candidates |
| GET | `/export` | Org role | ALIGNED | CSV export |
| GET | `/ranking/summary` | Org role | ALIGNED | Role summary |

## 8. Demo — `/demo`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| POST | `/refresh-db` | Local dev only | ALIGNED | Wipe runtime sessions, keep org/docs/resume/catalog |

## 9. Departments — `/departments`

This is an organization-level compatibility API. `department_id` is synthetic (`0`). There is no department table.

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `""` | Org role | ALIGNED (compat) | Returns one synthetic IT department |
| POST | `""` | Org owner | LEGACY (410) | Department creation disabled |
| GET | `/{department_id}` | Org role | ALIGNED (compat) | Synthetic department |
| PATCH | `/{department_id}` | Org owner | ALIGNED (compat) | Updates organization name/description |
| DELETE | `/{department_id}` | Org owner | LEGACY (410) | Department deletion disabled |
| GET | `/{department_id}/sessions` | Org role | ALIGNED | Organization sessions |
| GET | `/{department_id}/documents` | Org role | ALIGNED | Organization documents |
| POST | `/{department_id}/documents` | Org owner | ALIGNED | Upload organization document |
| DELETE | `/{department_id}/documents/{doc_id}` | Org owner | ALIGNED | Delete organization document |
| GET | `/{department_id}/templates` | Org role | ALIGNED | Organization templates |
| POST | `/{department_id}/templates` | Org owner | ALIGNED | Create organization template |
| GET | `/{department_id}/templates/{template_id}` | Org role | ALIGNED | Template detail |
| PUT | `/{department_id}/templates/{template_id}` | Org owner | ALIGNED | Update template |
| DELETE | `/{department_id}/templates/{template_id}` | Org owner | ALIGNED | Delete template |

## 10. Intelligence — `/intelligence`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| POST | `/build` | PENDING AUTH | ALIGNED | Build intelligence bundle |
| GET | `/brain/{session_id}` | PENDING AUTH | ALIGNED | Brain, evidence graph, timeline |

The evidence graph now comes from `interview_intelligence.evidence_graph`.

## 11. Invitations — `/invitations`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| POST | `""` | Org owner | ALIGNED | Invite candidate to a specific IT role |
| GET | `/{token}` | Public | ALIGNED | Verify candidate invitation |
| POST | `/{token}/accept` | Candidate | ALIGNED | Accept invitation and create session |

## 12. Marketplace / Opportunity Hub — `/marketplace`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `/organizations` | Public | ALIGNED | Browse organizations |
| GET | `/organizations/{slug}` | Public | ALIGNED | Organization profile + open listings |
| GET | `/interviews/{interview_id}` | Public | ALIGNED | Listing detail |
| POST | `/interviews/{interview_id}/start` | Public | ALIGNED | Start public interview |
| POST | `/interviews` | Org owner | ALIGNED | Create listing (`org_id` + `it_role_id`) |
| GET | `/org/{org_id}/interviews` | Org role | ALIGNED | List org listings |
| PUT | `/interviews/{interview_id}` | Org owner | ALIGNED | Update listing |
| DELETE | `/interviews/{interview_id}` | Org owner | ALIGNED | Delete listing |
| POST | `/interviews/{interview_id}/apply` | Optional candidate | ALIGNED | Apply with profile/resume |
| GET | `/org/{org_id}/applications` | Org role | ALIGNED | List applications |
| POST | `/applications/{application_id}/fit` | Org owner | ALIGNED | Set fit score/summary |
| POST | `/applications/{application_id}/invite` | Org owner | ALIGNED | Invite candidate; create session |
| POST | `/applications/{application_id}/outcome` | Org owner | ALIGNED | Record hired/rejected |
| POST | `/applications/{application_id}/respond` | Candidate | ALIGNED | Accept/decline invitation |

## 13. Public — `/public`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| POST | `/interviews/{token}/start` | Public | ALIGNED | Start interview by listing token |

## 14. Scorecards — `/orgs/{org_id}/scorecards`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `""` | Org role | ALIGNED | List scorecard templates |
| POST | `""` | Org owner | ALIGNED | Create scorecard template |
| GET | `/{template_id}` | Org role | ALIGNED | Get scorecard template |
| PUT | `/{template_id}` | Org owner | ALIGNED | Update scorecard template |
| DELETE | `/{template_id}` | Org owner | ALIGNED | Delete scorecard template |
| POST | `/{template_id}/sessions/{session_id}/calculate` | Org owner | ALIGNED | Calculate scorecard result |
| GET | `/sessions/{session_id}` | Org role | ALIGNED | Get scorecard result |

## 15. System — `/api/v1`

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `/health` | Public | ALIGNED | Health check |
| GET | `/orgs/{org_id}/llm-status` | Org owner | ALIGNED | LLM provider status |
| GET | `/orgs/{org_id}/llm-usage` | Org owner | ALIGNED | LLM usage |
| GET | `/orgs/{org_id}/email-templates` | Org owner | ALIGNED | List email templates |
| GET | `/orgs/{org_id}/email-templates/{name}` | Org owner | ALIGNED | Get email template |
| PUT | `/orgs/{org_id}/email-templates/{name}` | Org owner | ALIGNED | Update email template |

## 16. Interview Runtime

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `/interviews/{session_id}/summary` | Optional candidate | RUNTIME | Full session summary |
| WS | `/ws/interview/{session_id}` | Optional candidate token | RUNTIME | Live interview WebSocket |

WebSocket message types:
- `start_interview`
- `request_question`
- `submit_answer`
- `get_status`
- `ping`

## 17. Root / Health

| Method | Path | Auth | Status | Purpose |
|---|---|---|---|---|
| GET | `/` | Public | ALIGNED | Root status |
| GET/POST | `/health` | Public | ALIGNED | Legacy health check |

## 18. Unmounted Legacy Routers

These are not included in `app/main.py` and reference removed tables. Delete or rewrite later.

### Scheduling — `/scheduling`

- `POST /slots`
- `GET /slots`
- `POST /availability`
- `GET /available`
- `POST /book`
- `POST /bookings/{booking_id}/cancel`

### Calibration — `/orgs/{org_id}/calibration`

- `PUT /feedback/{session_id}`
- `GET /drift`
- `GET /drift/summary`

## 19. API Notes for Claude

- Do not add a department API. `/departments` is a compatibility shim.
- New listings require `it_role_id`, not `department_id`.
- New interview sessions require `it_role_id`.
- `public_interview_submissions.session_id` is nullable until the org invites.
- `public_interview_submissions` is the application record; do not create a separate applications table.
- Intelligence reads/writes use `interview_intelligence`.
- Organization access is owner-only via `organizations.owner_user_id`.
- Candidate practice sessions may have `org_id = NULL`.
- Add authentication to `/intelligence/*` before production.
