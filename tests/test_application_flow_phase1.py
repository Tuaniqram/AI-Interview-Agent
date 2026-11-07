"""Phase 1 of the candidate application flow: CV-required apply, resume helper,
claim-on-register / Google claim, and verified-only application history.

Uses a scripted fake DB (queued results, in call order) so no live services are needed.
"""
import io
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from httpx import ASGITransport, AsyncClient

from app.candidates import resume_service, service as candidate_service
from app.candidates.schemas import CandidateClaimRequest, CandidateRegisterRequest
from app.marketplace.schemas import ApplyRequest
from app.marketplace.service import apply_to_public_interview
from app.models.db import CandidateDocument, CandidateProfile, PublicInterviewSubmission

def _build_pdf(text: str) -> bytes:
    """Minimal valid single-page text PDF (with xref table) for tests."""
    stream = f"BT /F1 12 Tf 20 150 Td ({text}) Tj ET".encode()
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 300]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length %d>>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref_at)
    return bytes(out)


PDF_BYTES = _build_pdf("Python developer")


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def first(self):
        return self.value

    def one_or_none(self):
        # apply() selects (listing, org name); other lookups never call this.
        return None if self.value is None else (self.value, "Acme")


class ScriptedDB:
    """Returns queued results to successive ``execute`` calls (None once exhausted)."""

    def __init__(self, *results):
        self.queue = list(results)
        self.added = []
        self.commits = 0

    async def execute(self, stmt):
        return _Result(self.queue.pop(0) if self.queue else None)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        pass

    async def rollback(self):
        pass

    def of_type(self, cls):
        return [o for o in self.added if isinstance(o, cls)]


def _listing():
    return SimpleNamespace(
        id=uuid.uuid4(),
        is_open=True,
        org_id=uuid.uuid4(),
        title="Backend Engineer",
    )


def _pdf_upload(name="cv.pdf", content=PDF_BYTES):
    return UploadFile(file=io.BytesIO(content), filename=name)


def _guest_profile(**overrides):
    base = dict(
        id=uuid.uuid4(),
        email="alex@example.com",
        name="Alex",
        resume_url=None,
        password_hash=None,
        google_id=None,
        is_registered=False,
        is_verified=False,
        verified_at=None,
        verification_token_hash=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture(autouse=True)
def _resume_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(resume_service, "RESUMES_DIR", tmp_path)


# ── resume helper ────────────────────────────────────────────────────────


async def test_store_resume_creates_document_and_sets_profile_url():
    profile = _guest_profile()
    db = ScriptedDB()

    doc = await resume_service.store_candidate_resume(profile, _pdf_upload(), db)

    assert isinstance(doc, CandidateDocument)
    assert doc.candidate_id == profile.id
    assert doc.filename == "cv.pdf"
    assert doc.document_type == "resume"
    assert "Python developer" in doc.extracted_text
    assert profile.resume_url and profile.resume_url.endswith(".pdf")
    assert db.of_type(CandidateDocument) == [doc]


@pytest.mark.parametrize(
    "name,content,fragment",
    [
        pytest.param("cv.docx", PDF_BYTES, "Only PDF", id="not-pdf-extension"),
        pytest.param("cv.pdf", b"", "empty", id="empty"),
        pytest.param("cv.pdf", b"not a pdf at all", "valid PDF", id="bad-magic"),
        pytest.param(
            "cv.pdf",
            b"%PDF-" + b"x" * (resume_service.MAX_RESUME_BYTES + 1),
            "too large",
            id="too-large",
        ),
    ],
)
async def test_store_resume_rejects_bad_files(name, content, fragment):
    with pytest.raises(HTTPException) as exc:
        await resume_service.store_candidate_resume(
            _guest_profile(), _pdf_upload(name, content), ScriptedDB()
        )
    assert exc.value.status_code == 400
    assert fragment in exc.value.detail


# ── apply ────────────────────────────────────────────────────────────────


async def test_guest_apply_without_cv_is_400():
    # execute order: listing, profile lookup (none)
    db = ScriptedDB(_listing(), None)
    req = ApplyRequest(candidate_email="new@example.com", candidate_name="New Guest")

    with pytest.raises(HTTPException) as exc:
        await apply_to_public_interview("pi", req, db)

    assert exc.value.status_code == 400
    assert exc.value.detail == "CV is required"
    assert db.commits == 0


async def test_guest_apply_requires_name_and_valid_email():
    for email, name in [("not-an-email", "X"), ("a@b.com", "  ")]:
        with pytest.raises(HTTPException) as exc:
            await apply_to_public_interview(
                "pi",
                ApplyRequest(candidate_email=email, candidate_name=name),
                ScriptedDB(_listing()),
                resume=_pdf_upload(),
            )
        assert exc.value.status_code == 400


async def test_guest_apply_with_cv_creates_unregistered_profile_document_and_submission():
    pi = _listing()
    # execute order: listing, profile lookup (none), existing submission (none),
    # then org name + CV filename for the response
    db = ScriptedDB(pi, None, None, "Acme", "cv.pdf")
    req = ApplyRequest(candidate_email="new@example.com", candidate_name="New Guest")

    resp = await apply_to_public_interview("pi", req, db, resume=_pdf_upload())

    profile = db.of_type(CandidateProfile)[0]
    doc = db.of_type(CandidateDocument)[0]
    submission = db.of_type(PublicInterviewSubmission)[0]
    assert profile.is_registered is False
    assert profile.email == "new@example.com"
    assert doc.candidate_id == profile.id
    assert submission.candidate_profile_id == profile.id
    assert submission.resume_document_id == doc.id
    assert submission.fit_status == "pending"
    assert submission.status == "applied"
    assert db.commits == 1
    assert resp.has_resume is True
    assert resp.resume_filename == "cv.pdf"
    assert resp.fit_status == "pending"
    assert resp.org_name == "Acme"


async def test_guest_cannot_apply_as_registered_account():
    registered = _guest_profile(is_registered=True, is_verified=True)
    db = ScriptedDB(_listing(), registered)
    req = ApplyRequest(candidate_email="ALEX@example.com", candidate_name="Mallory")

    with pytest.raises(HTTPException) as exc:
        await apply_to_public_interview("pi", req, db, resume=_pdf_upload())

    assert exc.value.status_code == 409
    assert db.of_type(CandidateDocument) == []


async def test_guest_reapply_reuses_existing_guest_profile():
    guest = _guest_profile()
    # listing, profile lookup (found), existing submission (none), org name, filename
    db = ScriptedDB(_listing(), guest, None, "Acme", "cv.pdf")
    req = ApplyRequest(candidate_email="Alex@Example.com", candidate_name="Alex R")

    await apply_to_public_interview("pi", req, db, resume=_pdf_upload())

    assert db.of_type(CandidateProfile) == []  # no duplicate profile
    assert db.of_type(PublicInterviewSubmission)[0].candidate_profile_id == guest.id
    assert guest.name == "Alex R"


async def test_logged_in_apply_without_any_cv_is_400():
    me = _guest_profile(is_registered=True)
    # listing, latest resume document (none)
    db = ScriptedDB(_listing(), None)

    with pytest.raises(HTTPException) as exc:
        await apply_to_public_interview("pi", ApplyRequest(), db, candidate=me)

    assert exc.value.status_code == 400
    assert exc.value.detail == "CV is required"


async def test_logged_in_apply_uses_profile_cv_when_present():
    me = _guest_profile(is_registered=True)
    existing = SimpleNamespace(id=uuid.uuid4(), filename="profile.pdf")
    # listing, latest resume document, existing submission (none), org name, filename
    db = ScriptedDB(_listing(), existing, None, "Acme", "profile.pdf")

    resp = await apply_to_public_interview("pi", ApplyRequest(), db, candidate=me)

    submission = db.of_type(PublicInterviewSubmission)[0]
    assert submission.resume_document_id == existing.id
    assert submission.candidate_profile_id == me.id
    assert db.of_type(CandidateDocument) == []  # nothing new stored
    assert resp.resume_filename == "profile.pdf"


async def test_logged_in_apply_with_upload_links_new_document():
    me = _guest_profile(is_registered=True)
    db = ScriptedDB(_listing(), None, "Acme", "cv.pdf")

    await apply_to_public_interview("pi", ApplyRequest(), db, candidate=me, resume=_pdf_upload())

    doc = db.of_type(CandidateDocument)[0]
    assert db.of_type(PublicInterviewSubmission)[0].resume_document_id == doc.id
    assert me.resume_url == doc.document_metadata["path"]


async def test_logged_in_apply_rejects_someone_elses_document_id():
    me = _guest_profile(is_registered=True)
    # listing, lookup of resume_document_id scoped to this candidate (not found)
    db = ScriptedDB(_listing(), None)

    with pytest.raises(HTTPException) as exc:
        await apply_to_public_interview(
            "pi", ApplyRequest(resume_document_id=uuid.uuid4()), db, candidate=me
        )

    assert exc.value.status_code == 400


# ── claim on register / Google ───────────────────────────────────────────


@pytest.fixture
def claim_mail(monkeypatch):
    sent = []

    async def fake_send(to, subject, template_name, **vars_):
        sent.append(SimpleNamespace(to=to, template=template_name, vars=vars_))
        return True

    monkeypatch.setattr("app.services.email.send_email", fake_send)
    return sent


async def test_register_over_guest_profile_sets_no_password_and_emails_a_claim_link(claim_mail):
    guest = _guest_profile(resume_url="resumes/x.pdf", name="Alex")
    db = ScriptedDB(guest)

    resp = await candidate_service.register(
        CandidateRegisterRequest(email="Alex@Example.com", password="attacker-pass-1", name="Mallory"),
        db,
    )

    assert resp.claim_pending is True
    assert db.of_type(CandidateProfile) == []  # nothing created
    # Nothing the registrant typed is applied before inbox ownership is proven.
    assert guest.password_hash is None
    assert guest.is_registered is False
    assert guest.name == "Alex"
    assert guest.resume_url == "resumes/x.pdf"
    assert guest.verification_token_hash
    mail = claim_mail[0]
    assert mail.to == "alex@example.com" and mail.template == "account_claim.html"
    assert "/candidate/claim?token=" in mail.vars["CLAIM_URL"]


async def test_complete_claim_sets_password_registers_and_verifies_keeping_id():
    guest = _guest_profile()
    original_id = guest.id
    token = "claim-token-abc"
    guest.verification_token_hash = candidate_service._hash(token)
    guest.verification_sent_at = datetime.now(timezone.utc)
    db = ScriptedDB(guest)

    resp = await candidate_service.complete_claim(
        CandidateClaimRequest(token=token, password="my-real-password", name="Alex Rivera"), db
    )

    assert guest.id == original_id
    assert guest.is_registered is True and guest.is_verified is True
    assert guest.password_hash and guest.password_hash != "my-real-password"
    assert guest.name == "Alex Rivera"
    assert guest.verification_token_hash is None  # single use
    assert resp.tokens.access_token


@pytest.mark.parametrize("case", ["unknown", "expired", "already_registered"])
async def test_complete_claim_rejects_bad_links(case):
    guest = _guest_profile()
    guest.verification_token_hash = candidate_service._hash("t")
    guest.verification_sent_at = datetime.now(timezone.utc) - (
        timedelta(hours=25) if case == "expired" else timedelta(minutes=1)
    )
    guest.is_registered = case == "already_registered"
    db = ScriptedDB(None if case == "unknown" else guest)

    with pytest.raises(HTTPException) as exc:
        await candidate_service.complete_claim(CandidateClaimRequest(token="t", password="my-real-password"), db)

    assert exc.value.status_code == 400
    assert guest.password_hash is None


async def test_register_rejects_already_registered_email():
    registered = _guest_profile(is_registered=True)
    with pytest.raises(HTTPException) as exc:
        await candidate_service.register(
            CandidateRegisterRequest(email="alex@example.com", password="correct-horse", name="Eve"),
            ScriptedDB(registered),
        )
    assert exc.value.status_code == 409


async def test_register_with_different_email_creates_new_profile():
    guest = _guest_profile()
    db = ScriptedDB(None)  # lookup by the *new* email finds nothing

    await candidate_service.register(
        CandidateRegisterRequest(email="other@example.com", password="correct-horse", name="Other"),
        db,
    )

    created = db.of_type(CandidateProfile)
    assert len(created) == 1
    assert created[0].id != guest.id
    assert created[0].is_registered is True


async def test_google_login_claims_guest_profile_and_verifies():
    guest = _guest_profile()
    original_id = guest.id
    db = ScriptedDB(guest)

    await candidate_service.google_login(
        {"email": "alex@example.com", "sub": "g-123", "name": "Alex", "email_verified": True}, db
    )

    assert db.of_type(CandidateProfile) == []
    assert guest.id == original_id
    assert guest.google_id == "g-123"
    assert guest.is_registered is True
    assert guest.is_verified is True
    assert guest.password_hash is None


async def test_google_verification_discards_untrusted_password():
    claimed = _guest_profile(is_registered=True, password_hash="attacker-hash")
    await candidate_service.google_login(
        {"email": "alex@example.com", "sub": "g-1", "email_verified": True}, ScriptedDB(claimed)
    )
    assert claimed.password_hash is None
    assert claimed.is_verified is True


async def test_google_login_without_verified_email_stays_unverified():
    guest = _guest_profile()
    await candidate_service.google_login(
        {"email": "alex@example.com", "sub": "g-1", "email_verified": False}, ScriptedDB(guest)
    )
    assert guest.is_registered is True
    assert guest.is_verified is False


# ── HTTP: multipart contract + verified gating ───────────────────────────


@pytest.fixture
def api(monkeypatch):
    from app.auth.jwt import create_access_token
    from app.database.deps import get_db
    from app.main import app

    holder = SimpleNamespace(db=ScriptedDB(), evaluations=[])

    async def _db():
        yield holder.db

    async def _record_evaluation(application_id):
        holder.evaluations.append(application_id)  # never run the real LLM/DB evaluation

    monkeypatch.setattr("app.api.v1.marketplace.run_application_fit_evaluation", _record_evaluation)
    app.dependency_overrides[get_db] = _db
    holder.app = app
    holder.token = lambda cid: create_access_token(str(cid), token_type="candidate_access")
    yield holder
    app.dependency_overrides.clear()


async def test_http_guest_apply_multipart_without_cv_is_400(api):
    api.db = ScriptedDB(_listing(), None)
    async with AsyncClient(transport=ASGITransport(app=api.app), base_url="http://t") as client:
        r = await client.post(
            f"/api/v1/marketplace/interviews/{uuid.uuid4()}/apply",
            data={"candidate_email": "g@example.com", "candidate_name": "Guest"},
        )
    assert r.status_code == 400
    assert r.json()["detail"] == "CV is required"


async def test_http_guest_apply_multipart_with_cv_succeeds(api):
    api.db = ScriptedDB(_listing(), None, None, "Acme", "cv.pdf")
    async with AsyncClient(transport=ASGITransport(app=api.app), base_url="http://t") as client:
        r = await client.post(
            f"/api/v1/marketplace/interviews/{uuid.uuid4()}/apply",
            data={"candidate_email": "g@example.com", "candidate_name": "Guest"},
            files={"resume": ("cv.pdf", PDF_BYTES, "application/pdf")},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_resume"] is True
    assert body["fit_status"] == "pending"
    assert body["candidate_email"] == "g@example.com"
    assert api.evaluations == [body["id"]]  # evaluation is scheduled, not awaited


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/marketplace/applications/me"),
        ("post", f"/api/v1/marketplace/applications/{uuid.uuid4()}/respond"),
    ],
)
async def test_http_unverified_candidate_cannot_read_or_answer_history(api, method, path):
    unverified = _guest_profile(is_registered=True, is_verified=False)
    api.db = ScriptedDB(unverified)  # authenticate_candidate loads the profile
    headers = {"Authorization": f"Bearer {api.token(unverified.id)}"}
    async with AsyncClient(transport=ASGITransport(app=api.app), base_url="http://t") as client:
        kwargs = {"json": {"response": "accepted"}} if method == "post" else {}
        r = await getattr(client, method)(path, headers=headers, **kwargs)
    assert r.status_code == 403
