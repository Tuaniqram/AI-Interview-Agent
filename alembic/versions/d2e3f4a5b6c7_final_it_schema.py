"""final 33-table IT schema

Revision ID: d2e3f4a5b6c7
Revises: b1a2c3d4e5f6
Create Date: 2026-11-06

Preserves users, organizations, org invitations, auth/reset tokens, candidate
profiles, candidate documents/resumes, audit log, and department documents
(renamed to organization_documents). Rebuilds the interview, marketplace,
evaluation, and IT catalog surface from docs/it-scope/schema.sql.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "b1a2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs" / "it-scope" / "schema.sql"
SEED_PATH = ROOT / "docs" / "it-scope" / "seed-it-catalog.sql"

KEPT_TABLES = {
    "organizations",
    "users",
    "org_users",
    "org_invitations",
    "refresh_tokens",
    "user_password_reset_tokens",
    "candidate_profiles",
    "candidate_refresh_tokens",
    "candidate_password_reset_tokens",
    "candidate_documents",
    "audit_log",
    "organization_documents",
}

DROP_TABLES = [
    "interview_events",
    "v4_session_state",
    "integrity_events",
    "calibration_feedback",
    "candidate_evidence_requirements",
    "candidate_brains",
    "interview_blueprints",
    "scorecards",
    "company_brains",
    "evidence_graph",
    "observations",
    "consistency_checks",
    "interview_objectives",
    "evidence_store",
    "hypotheses",
    "interview_brain",
    "interview_timeline",
    "interview_intelligence",
    "scorecard_results",
    "interview_evaluations",
    "interview_messages",
    "interview_sessions",
    "public_interview_submissions",
    "public_interviews",
    "candidate_saved_listings",
    "candidate_sessions",
    "candidate_invitations",
    "interview_templates",
    "scorecard_templates",
    "bookings",
    "slot_availability",
    "interview_slots",
    "it_roles",
    "competencies",
    "role_competencies",
    "companies",
    "company_documents",
]


def _strip_comments(sql: str) -> str:
    return "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )


def _split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    in_single = False
    dollar_tag: str | None = None

    while i < len(sql):
        ch = sql[i]

        if dollar_tag is not None:
            if sql.startswith(dollar_tag, i):
                buf.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            buf.append(ch)
            i += 1
            continue

        if in_single:
            buf.append(ch)
            if ch == "'":
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    buf.append(sql[i + 1])
                    i += 2
                    continue
                in_single = False
            i += 1
            continue

        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue

        if ch == "$":
            match = re.match(r"\$[A-Za-z0-9_]*\$", sql[i:])
            if match:
                dollar_tag = match.group(0)
                buf.append(dollar_tag)
                i += len(dollar_tag)
                continue

        if ch == ";":
            statement = "".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def _prepare_schema_statements() -> tuple[list[str], list[str], list[str], list[str]]:
    raw = _strip_comments(SCHEMA_PATH.read_text(encoding="utf-8"))
    creates: list[str] = []
    indexes: list[str] = []
    triggers: list[str] = []
    others: list[str] = []

    for statement in _split_sql(raw):
        upper = statement.upper()

        if upper.startswith("CREATE TABLE"):
            match = re.match(r"CREATE TABLE\s+([a-z0-9_]+)", statement, re.I)
            if match and match.group(1) not in KEPT_TABLES:
                creates.append(statement)
            continue

        if upper.startswith("CREATE UNIQUE INDEX"):
            indexes.append(re.sub(r"^CREATE UNIQUE INDEX\s+", "CREATE UNIQUE INDEX IF NOT EXISTS ", statement, flags=re.I))
            continue

        if upper.startswith("CREATE INDEX"):
            indexes.append(re.sub(r"^CREATE INDEX\s+", "CREATE INDEX IF NOT EXISTS ", statement, flags=re.I))
            continue

        if upper.startswith("CREATE TRIGGER"):
            match = re.match(
                r"CREATE TRIGGER\s+([a-z0-9_]+)\s+.*?\s+ON\s+([a-z0-9_]+)",
                statement,
                re.I | re.S,
            )
            if match:
                name, table = match.group(1), match.group(2)
                triggers.append(f'DROP TRIGGER IF EXISTS "{name}" ON "{table}"')
                triggers.append(statement)
            continue

        if upper.startswith("ALTER TABLE CANDIDATE_DOCUMENTS") and "ADD CONSTRAINT" in upper:
            others.append(
                "ALTER TABLE candidate_documents DROP CONSTRAINT IF EXISTS candidate_documents_session_id_fkey"
            )
            others.append(
                "ALTER TABLE candidate_documents DROP CONSTRAINT IF EXISTS fk_candidate_documents_session"
            )
            others.append(statement)
            continue

        if upper.startswith(("CREATE EXTENSION", "CREATE OR REPLACE FUNCTION", "COMMENT ON")):
            others.append(statement)
            continue

    return creates, indexes, triggers, others


def _seed_statements() -> list[str]:
    raw = _strip_comments(SEED_PATH.read_text(encoding="utf-8"))
    return _split_sql(raw)


def upgrade() -> None:
    rename_statements = [
        "ALTER TABLE department_documents RENAME TO organization_documents",
        "ALTER TABLE organization_documents RENAME COLUMN department_id TO org_id",
        "ALTER TABLE organization_documents DROP CONSTRAINT IF EXISTS department_documents_department_id_fkey",
        "ALTER TABLE organization_documents ADD COLUMN IF NOT EXISTS org_uuid uuid",
        "ALTER TABLE organization_documents ADD COLUMN IF NOT EXISTS storage_path text",
        "ALTER TABLE organization_documents ADD COLUMN IF NOT EXISTS content_hash text",
        """
        UPDATE organization_documents d
        SET org_uuid = dep.org_id
        FROM departments dep
        WHERE d.org_id = dep.id
        """,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'organization_documents'
                  AND column_name = 'org_uuid'
            ) THEN
                ALTER TABLE organization_documents DROP COLUMN org_id;
                ALTER TABLE organization_documents RENAME COLUMN org_uuid TO org_id;
            END IF;
        END $$;
        """,
        "ALTER TABLE organization_documents ALTER COLUMN org_id SET NOT NULL",
        "ALTER TABLE organization_documents ADD CONSTRAINT organization_documents_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE",
        "CREATE INDEX IF NOT EXISTS idx_organization_documents_org ON organization_documents (org_id)",
        "CREATE INDEX IF NOT EXISTS idx_organization_documents_namespace ON organization_documents (pinecone_namespace)",
    ]
    for statement in rename_statements:
        op.execute(statement)

    for table in DROP_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')

    op.execute("DROP TABLE IF EXISTS departments CASCADE")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'organizations'
                  AND column_name = 'settings'
                  AND data_type = 'text'
            ) THEN
                ALTER TABLE organizations ALTER COLUMN settings DROP DEFAULT;
                ALTER TABLE organizations
                    ALTER COLUMN settings TYPE jsonb
                    USING CASE
                        WHEN settings IS NULL OR btrim(settings) = '' THEN '{}'::jsonb
                        WHEN btrim(settings) ~ '^[\\[{]' THEN settings::jsonb
                        ELSE '{}'::jsonb
                    END;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE organizations ALTER COLUMN settings SET DEFAULT '{}'::jsonb")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'audit_log'
                  AND column_name = 'details'
                  AND data_type = 'text'
            ) THEN
                ALTER TABLE audit_log ALTER COLUMN details DROP DEFAULT;
                ALTER TABLE audit_log
                    ALTER COLUMN details TYPE jsonb
                    USING CASE
                        WHEN details IS NULL OR btrim(details) = '' THEN '{}'::jsonb
                        WHEN btrim(details) ~ '^[\\[{]' THEN details::jsonb
                        ELSE '{}'::jsonb
                    END;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE audit_log ALTER COLUMN details SET DEFAULT '{}'::jsonb")

    creates, indexes, triggers, others = _prepare_schema_statements()
    for statement in creates + others + indexes + triggers:
        op.execute(statement)

    for statement in _seed_statements():
        op.execute(statement)


def downgrade() -> None:
    raise NotImplementedError("Final IT schema reset is not reversible")
