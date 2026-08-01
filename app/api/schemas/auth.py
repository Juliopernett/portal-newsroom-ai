"""HTTP schemas for auth (login/logout/me).

`UserOut` never includes `password_hash` — only `id`, `email`, `nombre`
ever cross the HTTP boundary for a `User`.
"""

from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Request body for `POST /auth/login`."""

    email: str
    password: str


class UserOut(BaseModel):
    """Response body for the authenticated user — used by login and /auth/me."""

    id: str
    email: str
    nombre: str
