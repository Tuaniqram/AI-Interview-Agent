# AI Interview Agent — IT-Only Scope

This folder is the **new source of truth** for the system after the scope change:
the product interviews **only for roles inside the IT field**.

Legacy documents are kept in [`../archive/`](../archive/) for reference only.
They do **not** define current requirements.

## Read in this order

| File | Purpose |
|---|---|
| [`02-glossary.md`](02-glossary.md) | Read first: every term and acronym, with its meaning before first use |
| [`01-scope-change.md`](01-scope-change.md) | The scope decision, the recommended approach, what is in/out, and the impact map |
| [`04-final-table-list.md`](04-final-table-list.md) | Final 30-table list, grouped by purpose, with removed/merged mapping |
| [`05-erd-student-level.md`](05-erd-student-level.md) | Student-level 15-table ERD, optional AI tables, Mermaid diagram, and relationship rules |
| [`schema.sql`](schema.sql) | Complete PostgreSQL DDL for the final 30-table schema |
| [`seed-it-catalog.sql`](seed-it-catalog.sql) | Seed data for all IT roles and IT competencies |
| [`03-database-schema.md`](03-database-schema.md) | Previous lean 25-table reference; superseded by the final table list |

## Rules for any future requirement change

1. **Scope first.** Any new feature must answer: *which IT role or IT function does this serve?*
2. **Define before abbreviating.** Every acronym and domain term gets a plain meaning in
   [`02-glossary.md`](02-glossary.md) before it is used in a requirement, table, or diagram.
3. **One owner user per organization.** `organizations.owner_user_id` replaces `org_users`;
   there are no teammate invitations.
4. **One organization can publish many interviews.** Interviews are rows in `public_interviews`;
   there is no department table.
5. **Roles come from the IT catalog.** Users select an IT role; they do not type a free-text role.
6. **Database rules are part of the requirement.** A requirement that cannot be represented in
   [`schema.sql`](schema.sql) is not ready to implement.
7. **Archive, do not silently delete.** Superseded documents move to `docs/archive/` and stay
   readable for traceability.

## Status

- Scope decision: **IT field only**
- IT role catalog: **179 roles across 23 IT families** (see [`seed-it-catalog.sql`](seed-it-catalog.sql))
- Competency catalog: **60 IT-relevant competencies**
- Database schema: **30 tables**, final design ready for ERD
- Supabase: **applied** (30 tables + `alembic_version`, IT catalog seeded: 179 roles / 60 competencies)
- Legacy docs: **archived, reference only**
- Application code: **backend aligned** (auth/org, documents, templates, marketplace, OH apply/invite/accept/outcome, consolidated intelligence persistence); frontend + IT taxonomy/prompts are next
