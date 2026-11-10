"""Report the current single-owner organization seed state."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select

from app.database.session import get_session_factory
from app.models.db import (
    CandidateInvitation,
    CandidateProfile,
    InterviewTemplate,
    ItRole,
    Organization,
    OrganizationDocument,
    User,
)


async def verify():
    factory = get_session_factory()
    async with factory() as session:
        async def count(model, *where):
            query = select(func.count()).select_from(model)
            for clause in where:
                query = query.where(clause)
            return await session.scalar(query)

        print(f"Users: {await count(User)}")
        print(f"Admins: {await count(User, User.is_admin.is_(True))}")
        print(f"Organizations: {await count(Organization)}")

        owners = (
            await session.execute(
                select(Organization.name, User.email)
                .join(User, User.id == Organization.owner_user_id)
                .order_by(Organization.name)
            )
        ).all()
        print("Owners:")
        for org_name, email in owners:
            print(f"  {org_name} -> {email}")

        owns_org = select(Organization.id).where(Organization.owner_user_id == User.id).exists()
        is_candidate = select(CandidateProfile.id).where(
            func.lower(CandidateProfile.email) == func.lower(User.email)
        ).exists()
        orphans = await session.scalar(
            select(func.count()).select_from(User).where(
                User.is_admin.is_(False), ~owns_org, ~is_candidate
            )
        )
        print(f"Orphan non-owner accounts: {orphans}")

        print(f"Organization documents: {await count(OrganizationDocument)}")
        print(f"Interview templates: {await count(InterviewTemplate)}")
        print(f"IT roles: {await count(ItRole)}")
        print(f"Candidate profiles: {await count(CandidateProfile)}")
        print(f"Candidate invitations: {await count(CandidateInvitation)}")


asyncio.run(verify())
