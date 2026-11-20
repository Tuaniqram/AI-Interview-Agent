# Plan: one `users` table for every account

Status: **proposal, not started.** Nothing here has been implemented. This is outside `docs/IMPLEMENTATION_PLAN.md`, so it needs
your explicit approval first (see "Decisions I need from you"). It does not touch the interview engine, scoring or prompts, so
the simulated-interview harness gate does not apply.

## Goal

Every person who can sign in is one row in `users`. Candidates keep a separate `candidate_profiles` table for candidate-only data
(resume, skills, phone, profile data). Login, token refresh, password reset and email verification are implemented once and use
one set of tables.

Not a goal: changing URLs the frontend calls, changing what candidates or hiring teams see, or merging organizations/interviews.

## Today (measured from the code and the live database)

| | `users` | `candidate_profiles` |
| --- | --- | --- |
| Who | organization owners, admins | candidates, including guests who only applied |
| Login data | `email` (unique), `name`, `password_hash` (required) | `email` (unique), `name`, `password_hash` (optional), `google_id` |
| Verification | none | `is_verified`, `verified_at`, `verification_token_hash`, `verification_sent_at`, `is_registered` |
| Other columns | `is_admin`, `is_active`, `avatar_url` | `phone`, `resume_url`, `skills`, `profile_data` |
| Refresh tokens | `refresh_tokens` | `candidate_refresh_tokens` |
| Reset tokens | `user_password_reset_tokens` | `candidate_password_reset_tokens` |
| JWT access type | `access` | `candidate_access` |
| Code | `app/auth/service.py`, `app/api/v1/auth.py` | `app/candidates/service.py`, `app/candidates/auth.py`, `app/api/v1/candidates.py` |

Live data (2026-11-20): 2 users, 1 candidate profile, 19 refresh tokens, 2 candidate refresh tokens. Small, so this is the cheapest
time to do it.

Tables that point at `candidate_profiles.id`: `candidate_documents`, `candidate_saved_listings`, `interview_sessions`,
`public_interview_submissions`, plus the two candidate token tables. Tables that point at `users.id`: `organizations.owner_user_id`,
`audit_log.user_id`, `candidate_invitations.created_by`, `public_interview_submissions` (two `*_decided_by` columns), `refresh_tokens`,
`user_password_reset_tokens`. About 17 backend files mention candidate profiles, 22 use `User`, 2 test files touch candidate profiles.

Two accounts with the same email can exist today (one in each table); nothing prevents it.

## Target design

`users` (identity, for everyone): existing columns, plus `google_id` (unique, nullable), `is_registered` (false = a guest who has no
password yet), `is_verified`, `verified_at`, `verification_token_hash`, `verification_sent_at`. `password_hash` becomes nullable.

`candidate_profiles` (candidate data only): `id` is **the same value as the user's id** (shared primary key, a foreign key to
`users.id`), plus `phone`, `resume_url`, `skills`, `profile_data`, timestamps. Because ids are kept, the six tables that point at
`candidate_profiles.id` need **no change**.

Gone after the last step: `candidate_refresh_tokens`, `candidate_password_reset_tokens`, and the identity columns on
`candidate_profiles` (`email`, `name`, `password_hash`, `google_id`, `is_registered`, `is_verified`, `verified_at`, `verification_*`).

No `role` column: what an account can do follows from what it has. A candidate has a `candidate_profiles` row, an organization owner
owns an organization, an admin has `is_admin`. A user can have several.

**Acting-as rule (the security-critical part).** Today a candidate token cannot reach hiring endpoints because it is a different token
type and a different table. With one table, the token carries an `actor` claim (`candidate` or `org`), set by which login endpoint
issued it. `authenticate_candidate` accepts only `actor=candidate` and requires a candidate profile; the hiring dependencies accept only
`actor=org`. A candidate token must never pass a hiring dependency, and the reverse; tests enforce this on every route group.

Guests: a person who applies without an account becomes a `users` row with `is_registered=false` and no password. Registering or
"claiming" later sets the password on that same row (replacing the separate claim flow).

## Steps (each is shippable on its own; the test suite, about 1,150 tests, must pass before each)

**Step 0: checks and backup (read-only).**
- Export `users`, `candidate_profiles`, and the four token tables from Supabase.
- Query for emails present in **both** tables. Stop and decide per row if any exist (see decision 3).

**Step 1: additive migration.** Add the new columns to `users`, make `password_hash` nullable, add the unique index on `google_id`.
Nothing reads them yet, so nothing changes for anyone. Tests: migration up and down.

**Step 2: data migration.** In one transaction: copy each `candidate_profiles` row into `users` **with the same id**; copy
`candidate_refresh_tokens` into `refresh_tokens` and `candidate_password_reset_tokens` into `user_password_reset_tokens` (same token
hashes, so signed-in candidates stay signed in); add the foreign key `candidate_profiles.id -> users.id`. Idempotent, and it records
what it copied so the down migration can remove exactly that. Test on a copy of the production data first.

**Step 3: code switch.** One account service for register, login, Google login, refresh, logout, forgot/reset password, verify and claim.
`app/candidates/service.py` keeps only profile, interviews, stats and practice. The endpoint URLs and response shapes stay the same, so
the frontend is unaffected. One access token type with the `actor` claim; the old `candidate_access` is still accepted for one release
(access tokens last 15 minutes, refresh tokens 7 days, and refresh tokens are carried over in step 2). The WebSocket token check and
the interview-access token keep working. New tests: the cross-access matrix above, guest apply then claim, Google login, reset, refresh
rotation, a person who is both an organization owner and a candidate, and an unclaimed guest cannot log in.

**Step 4: frontend.** Expected to need little or nothing, because URLs and shapes do not change. Check the two token stores
(`candidateToken.ts`, `authService.ts`) and `apiClient.ts`; change only if the token claim forces it.

**Step 5: clean-up, one release later.** Drop the two candidate token tables and the identity columns on `candidate_profiles`.

## Risks and how each is handled

| Risk | Handling |
| --- | --- |
| A candidate reaches a hiring feature | `actor` claim plus tests over every route group before step 3 ships |
| Same email already in both tables | step 0 finds them; resolved by hand before step 2 |
| Signed-in candidates get logged out | refresh-token hashes are copied; old access type accepted for one release |
| Migration fails halfway | single transaction; down migration; backup from step 0 |
| Guests cannot be claimed | covered by tests; guest rows keep `password_hash` null and `is_registered` false |
| Missed a reference to the old tables | grep list in this document plus the test suite; step 5 only after a clean release |

## Rollback

Steps 1 and 2 are reversible with their down migrations. Step 3 is a code change: redeploy the previous commit; the old tables are
still present and still hold the original rows until step 5, so nothing is lost. Step 5 is the only one-way step, which is why it waits
a release.

## Decisions I need from you

1. Approve the shared-id design (`candidate_profiles.id` = `users.id`).
2. Approve the acting-as rule (`actor` claim, no `role` column).
3. If an email exists in both tables: merge into one account (one person) or keep the older one and rename the other?
4. Is it acceptable that guests (applied, never registered) become `users` rows with no password?
5. Confirm a Supabase export before step 2.

Time is not estimated: step 3 is the largest, and I would size it after step 0 shows how many emails collide.
