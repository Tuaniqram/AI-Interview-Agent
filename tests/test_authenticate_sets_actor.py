"""``authenticate`` records the acting user on the request.

Audited marketplace handlers read ``request.state.user`` for the audit actor. Nothing used to assign it, so every
audit entry for those actions had no actor.
"""
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import State

from app.auth.jwt import create_access_token
from app.auth.middleware import authenticate


class _Result:
    def __init__(self, user):
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class _DB:
    def __init__(self, user):
        self.user = user

    async def execute(self, _statement):
        return _Result(self.user)


def _request():
    return SimpleNamespace(state=State())


def _creds(user_id):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=create_access_token(str(user_id)))


async def test_authenticated_user_is_recorded_on_the_request():
    user = SimpleNamespace(id=uuid.uuid4(), is_active=True)
    request = _request()
    returned = await authenticate(request, _creds(user.id), _DB(user))
    assert returned is user
    assert request.state.user is user
    assert str(request.state.user.id) == str(user.id)  # what the audit calls read


async def test_failed_authentication_leaves_no_actor():
    request = _request()
    with pytest.raises(HTTPException):
        await authenticate(request, _creds(uuid.uuid4()), _DB(None))
    assert not hasattr(request.state, "user")

    inactive = SimpleNamespace(id=uuid.uuid4(), is_active=False)
    with pytest.raises(HTTPException):
        await authenticate(request, _creds(inactive.id), _DB(inactive))
    assert not hasattr(request.state, "user")
