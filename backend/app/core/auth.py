"""Supabase JWT authentication dependency for FastAPI.

Instead of local JWT decoding (which requires matching the exact signing
algorithm and secret — fragile with Supabase Cloud), we verify the token
by calling Supabase's /auth/v1/user endpoint.  This works regardless of
the signing algorithm (HS256, RS256, EdDSA, etc.).
"""

from __future__ import annotations
import logging
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Module-level persistent HTTP client (created on first use, closed at shutdown)
_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """Get (or lazily create) the persistent async HTTP client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client


async def close_http_client() -> None:
    """Close the persistent HTTP client (called on app shutdown)."""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Verify the Supabase JWT via the Supabase Auth API and return the user ID.

    Calls GET /auth/v1/user with the bearer token.  Supabase verifies the
    signature and expiry server-side, returning the user object on success.

    Raises 401 if the token is missing, invalid, or expired.
    Raises 503 if the Supabase Auth service is unreachable.
    """
    token = credentials.credentials
    client = await get_http_client()

    try:
        response = await client.get(
            f"{settings.SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.SUPABASE_ANON_KEY,
            },
        )

        if response.status_code != 200:
            logger.warning(
                "Supabase auth verification failed (HTTP %d): %s",
                response.status_code,
                response.text[:200],
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        user_data = response.json()
        user_id = user_data.get("id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )

        return user_id

    except httpx.RequestError as exc:
        logger.error("Failed to reach Supabase Auth service: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )
