import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

class GoogleOAuth:
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    @classmethod
    async def get_tokens(cls, code: str) -> Dict[str, Any]:
        """Exchange auth code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                cls.GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()

    @classmethod
    async def get_user_info(cls, access_token: str) -> Dict[str, Any]:
        """Fetch user profile from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                cls.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

google_oauth = GoogleOAuth()
