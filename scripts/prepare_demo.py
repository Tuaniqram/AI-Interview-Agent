"""Prepare a clean single-organization demo.

Keeps Nova AI and its knowledge documents, keeps one verified candidate
(candidate@test.com), removes the other organizations and their data, and clears
old interview/listing/audit rows so the demo run starts from a clean state.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select, text

from app.auth.password import hash_password
from app.database.session import get_session_factory
from app.models.db import Organization, User

KEEP_ORG_SLUG = "nova-ai"
KEEP_USERS = ("admin@test.com", "nova@test.com")
KEEP_CANDIDATE = "candidate@test.com"


async def main() -> None:
    factory = get_session_factory()
    async with factory() as db:
        org = (await db.execute(
            select(Organization).where(Organization.slug == KEEP_ORG_SLUG)
        )).scalar_one_or_none()
        if org is None:
            raise SystemExit(f"Organization {KEEP_ORG_SLUG!r} not found")
        owner = (await db.execute(
            select(User).where(User.email == "nova@test.com")
        )).scalar_one_or_none()
        if owner is None or org.owner_user_id != owner.id:
            raise SystemExit("nova@test.com must be the owner of Nova AI")

        # Fresh interview data. Deleting the session cascades messages, evaluations,
        # evidence, hypotheses, brain snapshots, timeline, intelligence and scorecards.
        await db.execute(text("DELETE FROM interview_sessions"))
        await db.execute(text("DELETE FROM public_interviews"))
        await db.execute(text("DELETE FROM candidate_invitations"))
        await db.execute(text("DELETE FROM candidate_saved_listings"))
        await db.execute(text("DELETE FROM public_interview_submissions"))
        await db.execute(text("DELETE FROM audit_log"))
        await db.execute(text("DELETE FROM refresh_tokens"))
        await db.execute(text("DELETE FROM candidate_documents"))
        await db.execute(text("DELETE FROM interview_templates WHERE org_id = :org_id"), {"org_id": org.id})
        await db.execute(text("DELETE FROM scorecard_templates WHERE org_id = :org_id"), {"org_id": org.id})

        # One organization only. This cascades its documents, templates, listings and sessions.
        await db.execute(text("DELETE FROM organizations WHERE id <> :org_id"), {"org_id": org.id})
        await db.execute(
            text("DELETE FROM users WHERE email NOT IN ('admin@test.com', 'nova@test.com')")
        )
        await db.execute(
            text(
                "UPDATE users SET password_hash = :password, is_active = true "
                "WHERE email IN ('nova@test.com', 'admin@test.com')"
            ),
            {"password": hash_password("Admin123!")},
        )

        # One verified candidate.
        await db.execute(
            text(
                "UPDATE candidate_profiles SET is_registered = true, is_verified = true, "
                "password_hash = :password WHERE email = :email"
            ),
            {"password": hash_password("Test123!"), "email": KEEP_CANDIDATE},
        )
        await db.execute(
            text("DELETE FROM candidate_profiles WHERE email <> :email"),
            {"email": KEEP_CANDIDATE},
        )
        await db.commit()

        async def count(sql: str) -> int:
            return int(await db.scalar(text(sql)) or 0)

        print("Demo state prepared")
        print(f"  organization: {org.name} ({org.slug}) id={org.id}")
        print(f"  owner:        nova@test.com")
        print(f"  candidate:    {KEEP_CANDIDATE} / Test123! (verified)")
        print(f"  organizations: {await count('SELECT count(*) FROM organizations')}")
        print(f"  users:         {await count('SELECT count(*) FROM users')}")
        print(f"  candidates:    {await count('SELECT count(*) FROM candidate_profiles')}")
        print(f"  documents:     {await count('SELECT count(*) FROM organization_documents')}")
        print(f"  sessions:      {await count('SELECT count(*) FROM interview_sessions')}")
        print(f"  listings:      {await count('SELECT count(*) FROM public_interviews')}")


if __name__ == "__main__":
    asyncio.run(main())
