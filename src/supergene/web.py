"""FastAPI app with Supabase Auth and protected routes."""
from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, SecretStr

from supergene.auth import get_current_user, supabase_auth_headers, supabase_auth_url
from supergene.config import Settings, get_settings


app = FastAPI(title="supergene")


class LoginRequest(BaseModel):
    """Email/password credentials for Supabase Auth."""

    email: EmailStr
    password: SecretStr


class LoginResponse(BaseModel):
    """Session tokens returned by Supabase Auth."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int | None = None


@app.get("/health")
def health() -> dict[str, str]:
    """Unauthenticated health check."""
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    """Exchange email/password credentials for a Supabase Auth session."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                supabase_auth_url(settings, "token"),
                params={"grant_type": "password"},
                headers={
                    **supabase_auth_headers(settings),
                    "Content-Type": "application/json",
                },
                json={
                    "email": payload.email,
                    "password": payload.password.get_secret_value(),
                },
                timeout=10.0,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Supabase Auth",
        ) from exc

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if response.is_error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Supabase Auth rejected the login request",
        )

    session = response.json()
    return LoginResponse(
        access_token=session["access_token"],
        refresh_token=session["refresh_token"],
        token_type=session.get("token_type", "bearer"),
        expires_in=session.get("expires_in"),
    )


@app.get("/me")
async def me(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
) -> dict[str, Any]:
    """Protected route that returns the authenticated Supabase user."""
    return {"user": current_user}
