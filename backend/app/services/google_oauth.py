from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings


def get_google_auth_url(state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{settings.GOOGLE_AUTH_URL}?{urlencode(params)}"
    print(f"[Google OAuth] Auth URL: {url}")
    return url


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            settings.GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            print(f"[Google OAuth] Token exchange failed: {response.status_code} - {response.text}")
        response.raise_for_status()
        return response.json()



async def get_google_user_info(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            settings.GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()
