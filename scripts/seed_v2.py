"""Seed the demo data for the single-owner organization model.

Creates one system admin, two organizations (each with one owner), a candidate
profile, and optional role-based templates/invitations when the IT catalog is
already seeded. No member/viewer accounts and no departments.
"""
import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.database.session import get_session_factory
from app.models.db import (
    CandidateInvitation,
    CandidateProfile,
    InterviewTemplate,
    ItRole,
    Organization,
    User,
)


async def _add_owner(session: AsyncSession, *, email: str, name: str, ts: datetime) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("Admin123!"),
        name=name,
        is_admin=False,
        is_active=True,
        created_at=ts,
        updated_at=ts,
    )
    session.add(user)
    await session.flush()
    return user


async def _add_org(session: AsyncSession, *, name: str, slug: str, description: str, website: str, owner: User, ts: datetime) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        name=name,
        slug=slug,
        description=description,
        website=website,
        is_active=True,
        created_at=ts,
        updated_at=ts,
    )
    session.add(org)
    await session.flush()
    return org


async def seed():
    factory = get_session_factory()
    async with factory() as session:
        if await session.scalar(select(User.id).where(User.email == "admin@test.com")):
            print("Seed already applied (admin@test.com exists). Run reset_and_seed.py first.")
            return

        ts = datetime.now(timezone.utc)

        sys_admin = User(
            id=uuid.uuid4(),
            email="admin@test.com",
            password_hash=hash_password("Admin123!"),
            name="System Admin",
            is_admin=True,
            is_active=True,
            created_at=ts,
            updated_at=ts,
        )
        session.add(sys_admin)
        await session.flush()

        gulftex_owner = await _add_owner(session, email="gulftex@test.com", name="GulfTex Admin", ts=ts)
        gulftex = await _add_org(
            session,
            name="GulfTex Energy",
            slug="gulftex-energy",
            description="Oil and gas exploration and production company based in Houston, TX",
            website="https://gulftex.example.com",
            owner=gulftex_owner,
            ts=ts,
        )

        nova_owner = await _add_owner(session, email="nova@test.com", name="Nova Admin", ts=ts)
        nova = await _add_org(
            session,
            name="Nova AI",
            slug="nova-ai",
            description="AI-first technology company building intelligent developer tools",
            website="https://nova-ai.example.com",
            owner=nova_owner,
            ts=ts,
        )

        candidate_user = User(
            id=uuid.uuid4(),
            email="candidate@test.com",
            name="Test Candidate",
            password_hash=hash_password("Test123!"),
            is_registered=True,
            is_verified=True,
            created_at=ts,
            updated_at=ts,
        )
        session.add(candidate_user)
        await session.flush()
        candidate = CandidateProfile(
            id=candidate_user.id,
            skills="Python, FastAPI, React",
            created_at=ts,
            updated_at=ts,
        )
        session.add(candidate)
        await session.flush()

        role = (await session.execute(select(ItRole).order_by(ItRole.name).limit(1))).scalar_one_or_none()
        if role is None:
            print("IT catalog is empty. Run scripts/seed_it_catalog.py, then re-run this seed for templates/invitations.")
        else:
            for org, owner, job_role in (
                (gulftex, gulftex_owner, "Petroleum Engineer"),
                (nova, nova_owner, "Senior ML Engineer"),
            ):
                session.add(InterviewTemplate(
                    id=uuid.uuid4(),
                    org_id=org.id,
                    it_role_id=role.id,
                    name=f"{job_role} interview",
                    job_role_snapshot=job_role,
                    description=f"Starter template for {job_role}",
                    interview_style="STANDARD",
                    total_questions=10,
                ))
                session.add(CandidateInvitation(
                    id=uuid.uuid4(),
                    org_id=org.id,
                    it_role_id=role.id,
                    candidate_email=f"candidate+{org.slug}@test.com",
                    candidate_name="Invited Candidate",
                    job_role_snapshot=job_role,
                    token=f"test-invite-{org.slug}",
                    interview_config={"question_count": 5, "difficulty": "mid"},
                    status="pending",
                    expires_at=ts + timedelta(days=7),
                    created_by=owner.id,
                    created_at=ts,
                ))

        await session.commit()

        print("Seed complete!")
        print("  System admin:   admin@test.com / Admin123!   (is_admin=true, no org)")
        print("  GulfTex owner:  gulftex@test.com / Admin123!")
        print("  Nova AI owner:  nova@test.com / Admin123!")
        print("  Candidate:      candidate@test.com / Test123!")
        if role is None:
            print("  Templates/invitations: skipped (IT catalog empty)")
        else:
            print("  Templates/invitations: created for both organizations")


if __name__ == "__main__":
    asyncio.run(seed())
