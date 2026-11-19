"""A listing can only be changed or deleted by the organization that owns it.

``require_org_role`` proves the caller owns the organization named in the ``X-Org-Id`` header. The update and
delete routes then used to load the listing by id alone, so the owner of one organization could change another
organization's listing. These tests capture the SQL the service runs and the arguments the routes pass.
"""
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import marketplace as routes
from app.marketplace import service
from app.marketplace.schemas import UpdatePublicInterviewRequest

LISTING_ID = str(uuid.uuid4())
OWN_ORG = str(uuid.uuid4())


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class CapturingDB:
    """Records every statement as SQL text and returns the queued listing (or None)."""

    def __init__(self, listing=None):
        self.listing = listing
        self.sql: list[str] = []
        self.deleted = []
        self.commits = 0

    async def execute(self, statement):
        compiled = statement.compile()
        # SQL text plus the bound values, so a test can see both the column and the organization it is compared to.
        self.sql.append(str(compiled) + " " + " ".join(str(v) for v in compiled.params.values()))
        return _Result(self.listing)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.commits += 1


def _scoped(sql: str) -> bool:
    # Only the WHERE clause counts: the SELECT list names every column, org_id included.
    _, _, where = sql.partition("WHERE")
    return "public_interviews.org_id =" in where


async def test_delete_with_org_filters_by_organization():
    db = CapturingDB(listing=SimpleNamespace(id=LISTING_ID))
    await service.delete_public_interview(LISTING_ID, db, org_id=OWN_ORG)
    assert _scoped(db.sql[0]) and OWN_ORG in db.sql[0]
    assert db.deleted and db.commits == 1


async def test_delete_of_another_organizations_listing_is_not_found():
    db = CapturingDB(listing=None)  # the org-scoped query finds nothing
    with pytest.raises(HTTPException) as exc:
        await service.delete_public_interview(LISTING_ID, db, org_id=OWN_ORG)
    assert exc.value.status_code == 404
    assert not db.deleted and db.commits == 0


async def test_update_of_another_organizations_listing_is_not_found():
    db = CapturingDB(listing=None)
    with pytest.raises(HTTPException) as exc:
        await service.update_public_interview(
            LISTING_ID, UpdatePublicInterviewRequest(title="hijacked"), db, org_id=OWN_ORG
        )
    assert exc.value.status_code == 404
    assert _scoped(db.sql[0])
    assert db.commits == 0


async def test_unscoped_lookup_is_only_for_the_platform_admin_path():
    db = CapturingDB(listing=SimpleNamespace(id=LISTING_ID))
    await service.delete_public_interview(LISTING_ID, db)  # org_id omitted = admin
    assert not _scoped(db.sql[0])


class _AuditStub:
    def __init__(self, db):
        pass

    async def log(self, **kwargs):
        return None


@pytest.fixture
def recorded(monkeypatch):
    calls = {}

    async def fake_update(interview_id, req, db, org_id=None):
        calls["update_org"] = org_id
        return {"ok": True}

    async def fake_delete(interview_id, db, org_id=None):
        calls["delete_org"] = org_id

    monkeypatch.setattr(routes, "update_public_interview", fake_update)
    monkeypatch.setattr(routes, "delete_public_interview", fake_delete)
    monkeypatch.setattr(routes, "AuditLogService", _AuditStub)
    return calls


def _request():
    return SimpleNamespace(state=SimpleNamespace(), client=None)


@pytest.mark.parametrize("is_admin,expected", [(False, OWN_ORG), (True, None)])
async def test_routes_pass_the_header_organization_unless_admin(recorded, is_admin, expected):
    user = SimpleNamespace(is_admin=is_admin)
    await routes.update_listing(
        uuid.UUID(LISTING_ID), UpdatePublicInterviewRequest(title="t"), _request(),
        org_id=OWN_ORG, user=user, _=None, db=object(),
    )
    await routes.delete_listing(
        uuid.UUID(LISTING_ID), _request(), org_id=OWN_ORG, user=user, _=None, db=object(),
    )
    assert recorded["update_org"] == expected
    assert recorded["delete_org"] == expected
