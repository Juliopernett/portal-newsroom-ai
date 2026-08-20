"""HTTP schemas for auth (login/logout/me).

`UserOut` never includes `password_hash` — only `id`, `email`, `nombre`
ever cross the HTTP boundary for a `User`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request body for `POST /auth/login`.

    `max_length` on both fields (security audit 2026-08-20, L1) — without
    it, an oversized body reaches Argon2id (deliberately slow) or the rate
    limiter's dict key before anything rejects it. 254 is the practical
    RFC 5321 email limit; 256 is generous for any real password.
    """

    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class UserOut(BaseModel):
    """Response body for the authenticated user — used by login and /auth/me."""

    id: str
    email: str
    nombre: str
