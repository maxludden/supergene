"""Supabase Auth helpers for protected FastAPI routes."""
from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from supergene.config import Settings, get_settings


bearer_scheme = HTTPBearer(auto_error=False)


def supabase_auth_url(settings: Settings, path: str) -> str:
    """Build a Supabase Auth API URL."""
    return f"{str(settings.supabase_url).rstrip('/')}/auth/v1/{path.lstrip('/')}"


def supabase_auth_headers(settings: Settings, access_token: str | None = None) -> dict[str, str]:
    """Return headers for Supabase Auth API calls."""
    headers = {
        "apikey": settings.supabase_publishable_key,
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> dict[str, Any]:
    """Validate a Supabase access token and return the authenticated user."""
    if credentials is None:
        raise_unauthorized("Missing bearer token")

    settings = get_settings()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                supabase_auth_url(settings, "user"),
                headers=supabase_auth_headers(settings, credentials.credentials),
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Supabase Auth",
        ) from exc

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise_unauthorized("Invalid or expired bearer token")

    if response.is_error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase Auth rejected the user lookup",
        )

    return response.json()


def raise_unauthorized(detail: str) -> None:
    """Raise a standards-friendly bearer auth error."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
