from typing import Optional

import httpx
from fastapi import HTTPException, status

from app.config import settings

GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


async def verify_google_token(credential: str) -> dict:
    """Verify a Google sign-in token. Fails closed: without a configured client id the audience cannot be checked, so Google
    sign-in is switched off instead of accepting a token that was issued to some other application."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google sign-in is not configured")

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

    if data.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token audience does not match client ID",
        )
    if data.get("iss") not in GOOGLE_ISSUERS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token issuer")
    if not data.get("sub") or not data.get("email"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token has no account")
    # An unverified address proves nothing about who owns the inbox: signing in with it could take over someone else's account.
    if str(data.get("email_verified")).lower() != "true":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your Google email address is not verified")

    return {
        "email": data.get("email"),
        "name": data.get("name"),
        "sub": data.get("sub"),
        "avatar": data.get("picture"),
        "email_verified": True,
    }
