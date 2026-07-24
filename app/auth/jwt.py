from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60


def create_access_token(user_id: str, org_id: Optional[str] = None, token_type: str = "access") -> str:
    payload = {
        "sub": user_id,
        "type": token_type,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    if org_id:
        payload["org_id"] = org_id
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, token_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": token_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("exp") < datetime.now(timezone.utc).timestamp():
            raise jwt.ExpiredSignatureError("Token expired")
        return payload
    except jwt.PyJWTError as e:
        raise ValueError(str(e))
