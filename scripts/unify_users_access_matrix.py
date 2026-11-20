"""Cross-access matrix for the unified accounts, run against the REAL database schema inside a transaction that is always
rolled back (throwaway accounts are never stored). Exercises the real services, not mocks.

    venv/Scripts/python.exe scripts/unify_users_access_matrix.py
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth import service as org  # noqa: E402
from app.auth.password import hash_password  # noqa: E402
from app.auth.schemas import LoginRequest, RegisterRequest  # noqa: E402
from app.candidates import service as cand  # noqa: E402
from app.candidates.schemas import CandidateLoginRequest, CandidateRegisterRequest  # noqa: E402
from app.database.session import get_engine  # noqa: E402
from app.models.db import CandidateProfile, Organization, User  # noqa: E402

FAILED: list[str] = []
PW = "Matrix-Test-Pass-1"


def check(ok: bool, what: str) -> None:
    print(("  [ok ] " if ok else "  [FAIL] ") + what)
    if not ok:
        FAILED.append(what)


async def denied(coro, what: str, codes=(401, 403)) -> None:
    try:
        await coro
    except HTTPException as exc:
        check(exc.status_code in codes, f"{what} -> {exc.status_code}")
        return
    check(False, f"{what} -> was ALLOWED")


async def run(db: AsyncSession) -> None:
    tag = uuid.uuid4().hex[:8]
    org_email, cand_email, guest_email, both_email = (f"{n}-{tag}@matrix.invalid" for n in ("org", "cand", "guest", "both"))

    print("setup (throwaway):")
    org_resp = await org.register(RegisterRequest(email=org_email, password=PW, name="Org Owner", org_name=f"Matrix {tag}"), db)
    cand_resp = await cand.register(CandidateRegisterRequest(email=cand_email, password=PW, name="Cand"), db)
    guest = User(id=uuid.uuid4(), email=guest_email, name="Guest", password_hash=None, is_registered=False)
    db.add(guest)
    await db.flush()
    db.add(CandidateProfile(id=guest.id, user=guest))
    await db.flush()
    print("\nsign-in on the right side:")
    check(bool((await org.login(LoginRequest(email=org_email, password=PW), db)).tokens.access_token), "org owner can log in as org")
    check(bool((await cand.login(CandidateLoginRequest(email=cand_email, password=PW), db)).tokens.access_token), "candidate can log in as candidate")

    print("\nthe wrong side is refused:")
    await denied(org.login(LoginRequest(email=cand_email, password=PW), db), "candidate logs in as ORG")
    await denied(cand.login(CandidateLoginRequest(email=org_email, password=PW), db), "org owner logs in as CANDIDATE")
    await denied(org.login(LoginRequest(email=guest_email, password=PW), db), "guest logs in as org")
    await denied(cand.login(CandidateLoginRequest(email=guest_email, password=PW), db), "guest logs in as candidate")
    await denied(org.google_login({"email": cand_email, "sub": "g-x", "email_verified": True}, db), "candidate signs in to org via Google")
    await denied(org.google_login({"email": org_email, "sub": "g-x", "email_verified": False}, db), "unverified Google email (org)")
    await denied(cand.google_login({"email": cand_email, "sub": "g-x", "email_verified": False}, db), "unverified Google email (candidate)")

    print("\nrefresh tokens cannot cross over:")
    await denied(org.refresh(cand_resp.tokens.refresh_token, db), "candidate refresh token used as ORG refresh")
    await denied(cand.refresh(org_resp.tokens.refresh_token, db), "org refresh token used as CANDIDATE refresh")
    fresh_org = await org.refresh(org_resp.tokens.refresh_token, db)
    check(bool(fresh_org.refresh_token), "org refresh token still works for org")
    await denied(org.refresh(org_resp.tokens.refresh_token, db), "an already-used refresh token (rotation)")
    fresh_cand = await cand.refresh(cand_resp.tokens.refresh_token, db)
    check(bool(fresh_cand.refresh_token), "candidate refresh token still works for candidate")

    print("\none person with both roles keeps them separate:")
    both = await org.register(RegisterRequest(email=both_email, password=PW, name="Both", org_name=f"Both {tag}"), db)
    await cand.login(CandidateLoginRequest(email=both_email, password=PW), db) if False else None
    check(bool(both.tokens.refresh_token), "account that owns an org can be created")
    # An org owner without a candidate profile is refused by the candidate side (already proven above); give it one explicitly.
    owner = (await db.execute(__import__("sqlalchemy").select(User).where(User.email == both_email))).scalar_one()
    db.add(CandidateProfile(id=owner.id, user=owner))
    await db.flush()
    org_t = (await org.login(LoginRequest(email=both_email, password=PW), db)).tokens.refresh_token
    cand_t = (await cand.login(CandidateLoginRequest(email=both_email, password=PW), db)).tokens.refresh_token
    await denied(cand.refresh(org_t, db), "that person's ORG refresh token on the candidate side")
    await denied(org.refresh(cand_t, db), "that person's CANDIDATE refresh token on the org side")

    print("\ndeactivated accounts:")
    victim = (await db.execute(__import__("sqlalchemy").select(User).where(User.email == cand_email))).scalar_one()
    victim.is_active = False
    await db.flush()
    await denied(cand.login(CandidateLoginRequest(email=cand_email, password=PW), db), "deactivated candidate logs in")
    await denied(cand.refresh(fresh_cand.refresh_token, db), "deactivated candidate refreshes")


async def main() -> int:
    engine = get_engine()
    async with engine.connect() as conn:
        trans = await conn.begin()
        # commits made by the services only release a savepoint; the outer transaction is rolled back at the end
        db = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            await run(db)
        finally:
            await db.close()
            await trans.rollback()
    print("\ntransaction ROLLED BACK (nothing stored)")
    async with engine.connect() as conn:
        left = (await conn.exec_driver_sql("select count(*) from users where email like '%@matrix.invalid'")).scalar()
    check(left == 0, "no throwaway account is left in the database")
    await engine.dispose()
    print("\nRESULT:", "ALL CHECKS PASSED" if not FAILED else f"{len(FAILED)} CHECK(S) FAILED: " + "; ".join(FAILED))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
