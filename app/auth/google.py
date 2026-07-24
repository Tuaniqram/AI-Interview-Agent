from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.config import settings

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"


async def verify_google_token(credential: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GOOGLE_TOKEN_INFO_URL,
            params={"id_token": credential},
            timeout=10,
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    data = resp.json()

    if settings.GOOGLE_CLIENT_ID and data.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token audience does not match client ID",
        )

    return {
        "email": data.get("email"),
        "name": data.get("name"),
        "sub": data.get("sub"),
        "avatar": data.get("picture"),
        "email_verified": data.get("email_verified") == "true",
    }
