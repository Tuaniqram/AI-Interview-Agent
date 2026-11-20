"""Security rules of the unified accounts (one `users` table for hiring users and candidates)."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth import accounts, google
from app.auth import service as org_service
from app.auth.accounts import ACTOR_CANDIDATE, ACTOR_ORG, rotate_refresh_token
from app.auth.jwt import create_refresh_token
from app.auth.password import hash_password
from app.auth.schemas import LoginRequest
from app.candidates import service as candidate_service
from app.candidates.schemas import CandidateLoginRequest

pytestmark = pytest.mark.asyncio


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def first(self):
        return self.value


class FakeDB:
    def __init__(self, *results):
        self.queue = list(results)
        self.added = []

    async def execute(self, stmt):
        return _Result(self.queue.pop(0) if self.queue else None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


def _user(**kw):
    base = dict(id=uuid.uuid4(), email="a@x.com", name="A", password_hash=hash_password("right-password"),
                is_active=True, is_admin=False, is_registered=True, is_verified=True, google_id=None)
    base.update(kw)
    return SimpleNamespace(**base)


def _stored(user_id, token_id, actor, **kw):
    base = dict(user_id=user_id, token_hash=hashlib.sha256(token_id.encode()).hexdigest(), actor=actor,
                revoked=False, expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    base.update(kw)
    return SimpleNamespace(**base)


async def _allow(db, user):
    return True


# ---- refresh tokens are bound to the kind of session they were issued for ----------------------------
async def test_candidate_refresh_token_cannot_mint_a_hiring_session():
    user = _user()
    token = create_refresh_token(str(user.id), "jti-1")
    with pytest.raises(HTTPException) as exc:
        await rotate_refresh_token(FakeDB(_stored(user.id, "jti-1", ACTOR_CANDIDATE), user), token, ACTOR_ORG, allow=_allow)
    assert exc.value.status_code == 401


async def test_hiring_refresh_token_cannot_mint_a_candidate_session():
    user = _user()
    token = create_refresh_token(str(user.id), "jti-2")
    with pytest.raises(HTTPException) as exc:
        await rotate_refresh_token(FakeDB(_stored(user.id, "jti-2", ACTOR_ORG), user), token, ACTOR_CANDIDATE, allow=_allow)
    assert exc.value.status_code == 401


async def test_refresh_rejects_revoked_expired_and_other_users_tokens():
    user = _user()
    token = create_refresh_token(str(user.id), "jti-3")
    cases = [
        _stored(user.id, "jti-3", ACTOR_ORG, revoked=True),
        _stored(user.id, "jti-3", ACTOR_ORG, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
        _stored(uuid.uuid4(), "jti-3", ACTOR_ORG),
    ]
    for stored in cases:
        with pytest.raises(HTTPException):
            await rotate_refresh_token(FakeDB(stored, user), token, ACTOR_ORG, allow=_allow)


async def test_refresh_rejects_deactivated_account_and_does_not_revoke_before_checking():
    user = _user(is_active=False)
    stored = _stored(user.id, "jti-4", ACTOR_ORG)
    with pytest.raises(HTTPException):
        await rotate_refresh_token(FakeDB(stored, user), create_refresh_token(str(user.id), "jti-4"), ACTOR_ORG, allow=_allow)
    assert stored.revoked is False


async def test_refresh_rotates_a_valid_token():
    user = _user()
    stored = _stored(user.id, "jti-5", ACTOR_ORG)
    db = FakeDB(stored, user)
    got, new_token = await rotate_refresh_token(db, create_refresh_token(str(user.id), "jti-5"), ACTOR_ORG, allow=_allow)
    assert got is user and new_token and stored.revoked is True
    assert db.added and db.added[0].actor == ACTOR_ORG


# ---- who may sign in where -----------------------------------------------------------------------------
async def test_candidate_only_account_cannot_get_a_hiring_session(monkeypatch):
    user = _user()
    # user lookup, then "owns an organization?" -> no
    with pytest.raises(HTTPException) as exc:
        await org_service.login(LoginRequest(email="a@x.com", password="right-password"), FakeDB(user, None))
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid email or password"


async def test_guest_account_without_password_cannot_log_in_anywhere():
    guest = _user(password_hash=None, is_registered=False)
    for call in (
        org_service.login(LoginRequest(email="a@x.com", password="anything-at-all"), FakeDB(guest)),
        candidate_service.login(CandidateLoginRequest(email="a@x.com", password="anything-at-all"), FakeDB(guest)),
    ):
        with pytest.raises(HTTPException) as exc:
            await call
        assert exc.value.status_code == 401


async def test_hiring_only_account_cannot_use_candidate_login():
    user = _user()
    # user lookup, then candidate profile -> none
    with pytest.raises(HTTPException) as exc:
        await candidate_service.login(CandidateLoginRequest(email="a@x.com", password="right-password"), FakeDB(user, None))
    assert exc.value.status_code == 401


async def test_unknown_email_gets_same_error_as_wrong_password():
    user = _user()
    with pytest.raises(HTTPException) as unknown:
        await candidate_service.login(CandidateLoginRequest(email="no@x.com", password="whatever-1"), FakeDB(None))
    with pytest.raises(HTTPException) as wrong:
        await candidate_service.login(CandidateLoginRequest(email="a@x.com", password="wrong-password"), FakeDB(user))
    assert unknown.value.detail == wrong.value.detail and unknown.value.status_code == wrong.value.status_code


async def test_hiring_google_login_refuses_candidate_account_and_other_google_identity():
    candidate = _user(google_id="g-1")
    with pytest.raises(HTTPException):  # not a hiring account
        await org_service.google_login({"email": "a@x.com", "sub": "g-1", "email_verified": True}, FakeDB(candidate, None))
    admin = _user(is_admin=True, google_id="g-original")
    with pytest.raises(HTTPException):  # same email, different Google identity
        await org_service.google_login({"email": "a@x.com", "sub": "g-attacker", "email_verified": True}, FakeDB(admin))


async def test_google_login_requires_verified_email_in_both_services():
    for fn in (org_service.google_login, candidate_service.google_login):
        with pytest.raises(HTTPException) as exc:
            await fn({"email": "a@x.com", "sub": "g", "email_verified": False}, FakeDB())
        assert exc.value.status_code == 401


# ---- Google token verification fails closed -------------------------------------------------------------
class _Resp:
    status_code = 200

    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def _patch_google(monkeypatch, data, client_id="cid"):
    monkeypatch.setattr(google.settings, "GOOGLE_CLIENT_ID", client_id, raising=False)

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, *a, **k):
            return _Resp(data)

    monkeypatch.setattr(google.httpx, "AsyncClient", lambda *a, **k: _Client())


GOOD = {"aud": "cid", "iss": "https://accounts.google.com", "sub": "s", "email": "a@x.com", "email_verified": "true"}


async def test_google_token_without_configured_client_id_is_refused(monkeypatch):
    _patch_google(monkeypatch, GOOD, client_id="")
    with pytest.raises(HTTPException) as exc:
        await google.verify_google_token("t")
    assert exc.value.status_code == 503


@pytest.mark.parametrize("change", [{"aud": "other-app"}, {"iss": "https://evil.example"}, {"email_verified": "false"}, {"sub": ""}])
async def test_google_token_checks_audience_issuer_verified_and_subject(monkeypatch, change):
    _patch_google(monkeypatch, {**GOOD, **change})
    with pytest.raises(HTTPException) as exc:
        await google.verify_google_token("t")
    assert exc.value.status_code == 401


async def test_good_google_token_is_accepted(monkeypatch):
    _patch_google(monkeypatch, GOOD)
    assert (await google.verify_google_token("t"))["email_verified"] is True


# ---- password reset signs the account out everywhere ---------------------------------------------------
async def test_password_reset_revokes_all_sessions(monkeypatch):
    user = _user()
    reset = SimpleNamespace(user_id=user.id, used=False)
    revoked = []

    async def fake_revoke(db, user_id, actor=None):
        revoked.append((user_id, actor))

    monkeypatch.setattr(accounts, "revoke_all_sessions", fake_revoke)
    await accounts.finish_password_reset(FakeDB(reset, user), "tok", "a-new-password-1")
    assert reset.used is True
    assert revoked == [(user.id, None)]  # None = every kind of session
    assert user.password_hash and user.password_hash != "a-new-password-1"


async def test_password_reset_with_bad_token_or_inactive_account_is_the_same_error():
    user = _user(is_active=False)
    for db in (FakeDB(None), FakeDB(SimpleNamespace(user_id=user.id, used=False), user)):
        with pytest.raises(HTTPException) as exc:
            await accounts.finish_password_reset(db, "tok", "a-new-password-1")
        assert exc.value.status_code == 400
