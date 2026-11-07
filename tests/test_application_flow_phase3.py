"""Phase 3 of the candidate application flow: invite emails, public (no-login)
invitation lookup/respond, and the invite guards. Services and email are faked."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.marketplace import notifications as notif
from app.marketplace import service as ms
from app.models.db import InterviewSession

NOW = datetime.now(timezone.utc)


def _session(**o):
    base = dict(
        id=uuid.uuid4(),
        status="initiating",
        invite_token="tok123",
        invite_expires_at=NOW + timedelta(days=5),
    )
    base.update(o)
    return SimpleNamespace(**base)


def _submission(**o):
    base = dict(
        id=uuid.uuid4(),
        session_id=None,
        candidate_name="Alex",
        candidate_email="alex@example.com",
        status="interview_offered",
        org_decision="invited",
        candidate_response="pending",
        candidate_responded_at=None,
        outcome="pending",
        invited_at=None,
        org_decided_by=None,
        org_decided_at=None,
        fit_status="completed",
    )
    base.update(o)
    return SimpleNamespace(**base)


PI = SimpleNamespace(id=uuid.uuid4(), org_id=uuid.uuid4(), it_role_id=uuid.uuid4(), title="Backend Engineer",
                     level_code="mid", interview_mode="typing")


class FakeDB:
    def __init__(self, *results):
        self.queue = list(results)
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        value = self.queue.pop(0) if self.queue else None
        return SimpleNamespace(scalar_one_or_none=lambda: value, one_or_none=lambda: value)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        pass


@pytest.fixture
def invitation(monkeypatch):
    """A resolvable invitation: submission + session + listing, token 'tok123'."""
    session = _session()
    sub = _submission(session_id=session.id)

    async def get_invitation(token, db):
        if token != "tok123":
            raise HTTPException(status_code=404, detail="Invitation not found")
        return sub, session, PI, "Acme"

    monkeypatch.setattr(ms, "_get_invitation", get_invitation)
    return SimpleNamespace(sub=sub, session=session)


# ── public invitation page ───────────────────────────────────────────────


async def test_view_invitation_shows_details_without_session_before_accept(invitation):
    inv = await ms.get_application_invitation("tok123", FakeDB())
    assert inv.org_name == "Acme"
    assert inv.job_title == "Backend Engineer"
    assert inv.candidate_email == "alex@example.com"
    assert inv.can_respond is True
    assert inv.expired is False
    assert inv.session_id is None  # not revealed until accepted
    assert inv.access_token is None  # no interview credential before accepting


async def test_unknown_token_is_404(invitation):
    with pytest.raises(HTTPException) as exc:
        await ms.get_application_invitation("nope", FakeDB())
    assert exc.value.status_code == 404


async def test_guest_accept_returns_session_id_and_updates_application(invitation):
    db = FakeDB()
    inv = await ms.respond_to_invitation("tok123", "accepted", db)

    assert inv.candidate_response == "accepted"
    assert inv.session_id == invitation.session.id  # guest can now start the interview
    from app.auth.interview_access import verify_interview_access_token

    # ...and holds a credential for exactly that session (the WebSocket requires it)
    assert verify_interview_access_token(inv.access_token) == str(invitation.session.id)
    assert invitation.sub.status == "interview_accepted"
    assert invitation.sub.candidate_responded_at is not None
    assert invitation.session.status == "initiating"  # stays startable
    assert db.commits == 1


async def test_decline_cancels_the_session(invitation):
    db = FakeDB(invitation.session)  # _record_candidate_response loads the session
    inv = await ms.respond_to_invitation("tok123", "declined", db)

    assert inv.candidate_response == "declined"
    assert inv.session_id is None
    assert inv.access_token is None
    assert inv.can_respond is False
    assert invitation.sub.status == "interview_declined"
    assert invitation.session.status == "cancelled"


async def test_repeating_the_same_answer_is_idempotent(invitation):
    await ms.respond_to_invitation("tok123", "accepted", FakeDB())
    db = FakeDB()
    again = await ms.respond_to_invitation("tok123", "accepted", db)
    assert again.session_id == invitation.session.id
    assert db.commits == 0  # reopened email link: nothing is rewritten


async def test_changing_a_given_answer_is_409(invitation):
    await ms.respond_to_invitation("tok123", "accepted", FakeDB())
    with pytest.raises(HTTPException) as exc:
        await ms.respond_to_invitation("tok123", "declined", FakeDB())
    assert exc.value.status_code == 409


async def test_expired_invitation_is_410_and_not_respondable(invitation):
    invitation.session.invite_expires_at = NOW - timedelta(days=1)

    view = await ms.get_application_invitation("tok123", FakeDB())
    assert view.expired is True and view.can_respond is False

    with pytest.raises(HTTPException) as exc:
        await ms.respond_to_invitation("tok123", "accepted", FakeDB())
    assert exc.value.status_code == 410
    assert invitation.sub.candidate_response == "pending"


async def test_closed_application_cannot_be_answered(invitation):
    invitation.sub.outcome = "rejected"
    with pytest.raises(HTTPException) as exc:
        await ms.respond_to_invitation("tok123", "accepted", FakeDB())
    assert exc.value.status_code == 409


async def test_invalid_response_value_is_400(invitation):
    with pytest.raises(HTTPException) as exc:
        await ms.respond_to_invitation("tok123", "maybe", FakeDB())
    assert exc.value.status_code == 400


async def test_http_unknown_token_returns_404():
    from app.database.deps import get_db
    from app.main import app

    async def _db():
        yield FakeDB(None)  # token lookup finds nothing

    app.dependency_overrides[get_db] = _db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/v1/marketplace/application-invitations/deadbeef")
            assert r.status_code == 404
            r = await c.post(
                "/api/v1/marketplace/application-invitations/deadbeef/respond", json={"response": "accepted"}
            )
            assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ── invite action ────────────────────────────────────────────────────────


@pytest.fixture
def invite_env(monkeypatch):
    holder = SimpleNamespace(sub=_submission(org_decision="pending", status="evaluated", session_id=None))

    async def get_org_application(application_id, org_id, db):
        return holder.sub, PI

    async def response_for(submission, pi, db):
        return SimpleNamespace(org_decision=submission.org_decision, status=submission.status)

    monkeypatch.setattr(ms, "_get_org_application", get_org_application)
    monkeypatch.setattr(ms, "_application_response_for", response_for)
    return holder


async def test_invite_creates_session_with_token_and_marks_invited(invite_env):
    sub = invite_env.sub
    sub.candidate_profile_id = uuid.uuid4()
    db = FakeDB()

    resp = await ms.invite_application("a", "o", str(uuid.uuid4()), db)

    created = [o for o in db.added if isinstance(o, InterviewSession)]
    assert len(created) == 1
    assert created[0].invite_token and len(created[0].invite_token) == 32
    assert created[0].invite_expires_at > NOW + timedelta(days=6)
    assert created[0].candidate_profile_id == sub.candidate_profile_id
    assert sub.session_id == created[0].id
    assert (resp.org_decision, resp.status) == ("invited", "interview_offered")
    assert sub.invited_at is not None


async def test_resend_reuses_session_and_extends_expiry(invite_env):
    old = _session(invite_expires_at=NOW + timedelta(hours=1))
    invite_env.sub.session_id = old.id
    db = FakeDB(old)

    await ms.invite_application("a", "o", None, db)

    assert [o for o in db.added if isinstance(o, InterviewSession)] == []  # no duplicate session
    assert old.invite_token == "tok123"  # same link keeps working
    assert old.invite_expires_at > NOW + timedelta(days=6)


@pytest.mark.parametrize("field,value", [
    ("candidate_response", "accepted"),
    ("candidate_response", "declined"),
    ("outcome", "hired"),
    ("outcome", "rejected"),
    ("org_decision", "rejected"),
])
async def test_invite_refused_when_answered_or_closed(invite_env, field, value):
    setattr(invite_env.sub, field, value)
    with pytest.raises(HTTPException) as exc:
        await ms.invite_application("a", "o", None, FakeDB())
    assert exc.value.status_code == 409
    assert invite_env.sub.status == "evaluated"  # nothing was clobbered


# ── emails ───────────────────────────────────────────────────────────────


@pytest.fixture
def mail(monkeypatch):
    sent = []

    async def fake_send(to, subject, template_name, **vars_):
        sent.append(SimpleNamespace(to=to, subject=subject, template=template_name, vars=vars_))
        return True

    monkeypatch.setattr("app.services.email.send_email", fake_send)
    monkeypatch.setattr(notif.settings, "APP_URL", "https://app.example.com/")
    return sent


def _data(**o):
    base = dict(email="alex@example.com", name="Alex", job_role="Backend Engineer", org_name="Acme",
                outcome="pending", invite_token="tok123", invite_expires_at=NOW + timedelta(days=7))
    base.update(o)
    return base


def _loader(monkeypatch, data):
    async def load(application_id):
        return data

    monkeypatch.setattr(notif, "_load", load)


async def test_invitation_email_links_to_public_invite_page(mail, monkeypatch):
    _loader(monkeypatch, _data())

    assert await notif.send_application_invitation_email("app-1") is True

    m = mail[0]
    assert m.to == "alex@example.com"
    assert m.template == "application_invitation.html"
    assert m.vars["INVITE_URL"] == "https://app.example.com/application-invite/tok123"
    assert m.vars["APP_URL"] == "https://app.example.com"
    assert m.vars["ORG_NAME"] == "Acme" and m.vars["JOB_ROLE"] == "Backend Engineer"
    assert "Backend Engineer" in m.subject


async def test_email_variables_are_html_escaped(mail, monkeypatch):
    _loader(monkeypatch, _data(name="<script>alert(1)</script>", org_name='Acme "R&D"'))

    await notif.send_application_invitation_email("app-1")

    v = mail[0].vars
    assert "<script>" not in v["CANDIDATE_NAME"] and "&lt;script&gt;" in v["CANDIDATE_NAME"]
    assert "&amp;" in v["ORG_NAME"] and "&quot;" in v["ORG_NAME"]


async def test_invitation_email_skipped_without_token(mail, monkeypatch):
    _loader(monkeypatch, _data(invite_token=None))
    assert await notif.send_application_invitation_email("app-1") is False
    assert mail == []


async def test_email_failure_never_raises(monkeypatch):
    _loader(monkeypatch, _data())

    async def boom(**kwargs):
        raise RuntimeError("resend down")

    monkeypatch.setattr("app.services.email.send_email", lambda *a, **k: boom())
    assert await notif.send_application_invitation_email("app-1") is False  # swallowed, logged


async def test_disabled_email_returns_false_without_error(monkeypatch):
    _loader(monkeypatch, _data())
    monkeypatch.setattr("app.services.email._email_enabled", False)
    assert await notif.send_application_invitation_email("app-1") is False


async def test_received_email_points_to_registration(mail, monkeypatch):
    _loader(monkeypatch, _data())
    await notif.send_application_received_email("app-1")
    assert mail[0].template == "application_received.html"
    assert mail[0].vars["REGISTER_URL"] == "https://app.example.com/candidate/register"


@pytest.mark.parametrize("outcome,expected", [("hired", "Good news"), ("rejected", "Application update")])
async def test_outcome_email_only_for_final_outcomes(mail, monkeypatch, outcome, expected):
    _loader(monkeypatch, _data(outcome=outcome))
    assert await notif.send_application_outcome_email("app-1") is True
    assert mail[0].vars["HEADLINE"] == expected


async def test_outcome_email_not_sent_while_pending(mail, monkeypatch):
    _loader(monkeypatch, _data(outcome="pending"))
    assert await notif.send_application_outcome_email("app-1") is False
    assert mail == []


def test_application_templates_render_with_all_variables():
    from app.services.email import _render

    common = {"APP_URL": "https://a", "CANDIDATE_NAME": "A", "ORG_NAME": "O", "JOB_ROLE": "R"}
    cases = {
        "application_received.html": {**common, "REGISTER_URL": "https://a/r"},
        "application_invitation.html": {**common, "INVITE_URL": "https://a/i", "EXPIRES_AT": "01 Jan 2030"},
        "application_outcome.html": {**common, "HEADLINE": "H", "MESSAGE": "M"},
    }
    for name, variables in cases.items():
        rendered = _render(name, **variables)
        assert "${" not in rendered, f"{name} has unfilled placeholders"
