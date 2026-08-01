"""Routes for authentication: login, logout, and "who am I".

Session-based, not JWT — see `core.entities.session.Session`'s docstring
for why. The raw session token only ever exists in the response cookie;
everywhere else (`core.entities.session.Session.token_hash`, the
database) only its SHA-256 hash is stored.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import (
    SESSION_COOKIE_NAME,
    get_current_session,
    get_current_user,
    get_password_hasher,
    get_unit_of_work,
    hash_session_token,
)
from app.api.schemas.auth import LoginRequest, UserOut
from config.settings import get_settings
from core.entities.session import Session as SessionEntity
from core.entities.user import User
from core.ports.password_hasher import PasswordHasher
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(prefix="/auth", tags=["auth"])

# A real Argon2id hash of an arbitrary, never-used password — not a
# hand-typed placeholder string. Verified against when the email isn't
# found, so a login attempt takes roughly the same time either way;
# `verify()` must actually run the full (deliberately slow) computation
# for that to work — a malformed hash would raise `InvalidHashError` and
# return fast, defeating the whole point.
_DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$WwazUiTYOWVrTQTeKpFt8w"
    "$cf+JKbRh5JqRBbmxrlpRLqspsxuKrQJj5wmbvqlZ1x0"
)


def _invalid_credentials() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")


def _set_session_cookie(response: Response, token: str, ttl_hours: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=ttl_hours * 3600,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
    )


@router.post("/login", response_model=UserOut)
def login(
    payload: LoginRequest,
    response: Response,
    uow: UnitOfWork = Depends(get_unit_of_work),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
) -> User:
    """Verify credentials, open a session, and set its cookie."""
    user = uow.users.get_by_email(payload.email)
    if user is None:
        password_hasher.verify(payload.password, _DUMMY_HASH)  # constant-time-ish decoy
        raise _invalid_credentials()
    if not password_hasher.verify(payload.password, user.password_hash):
        raise _invalid_credentials()

    settings = get_settings()
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session = SessionEntity(
        user_id=user.id,
        token_hash=hash_session_token(token),
        created_at=now,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
    )
    uow.sessions.save(session)
    uow.commit()

    _set_session_cookie(response, token, settings.session_ttl_hours)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session: SessionEntity = Depends(get_current_session),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> None:
    """Delete the current session server-side and clear its cookie."""
    uow.sessions.delete(session.id)
    uow.commit()
    response.delete_cookie(SESSION_COOKIE_NAME)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user."""
    return user
