"""FastAPI dependency injection for the internal API.

The only place in `app/api/` that touches `database.engine`/
`database.unit_of_work`/`security.password_hasher` directly — every route
handler depends on the `core.ports` abstractions, never the concrete
adapters, so tests can override these to point at a throwaway database
instead.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import Cookie, Depends, HTTPException, status

from agents.storage.local_disk import LocalDiskMediaStorage
from agents.wordpress.client import WordPressCMSPublisher
from config.settings import get_settings
from core.entities.session import Session as SessionEntity
from core.entities.user import User
from core.ports.cms_publisher import CMSPublisher
from core.ports.media_storage import MediaStorage
from core.ports.password_hasher import PasswordHasher
from core.ports.unit_of_work import UnitOfWork
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork
from security.login_rate_limiter import LoginRateLimiter
from security.password_hasher import Argon2IdPasswordHasher

SESSION_COOKIE_NAME = "session_token"


def get_unit_of_work() -> Iterator[UnitOfWork]:
    """Yield a `UnitOfWork` scoped to a single request.

    Commit is never implicit — a route handler that doesn't call
    `uow.commit()` gets a clean rollback when the request ends, the same
    "no commit means nothing happened" discipline `SqlAlchemyUnitOfWork`
    already guarantees.
    """
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        yield uow


def get_password_hasher() -> PasswordHasher:
    """Return the password hasher used to check credentials at login."""
    return Argon2IdPasswordHasher()


@lru_cache
def get_login_rate_limiter() -> LoginRateLimiter:
    """Return the process-wide login rate limiter (security audit
    2026-08-20, M1) — a singleton via `lru_cache`, the same pattern
    `config.settings.get_settings` already uses, so its state persists
    across requests within this process without needing a database table.
    """
    return LoginRateLimiter()


def get_cms_publisher() -> CMSPublisher:
    """Return the CMS publisher used to create WordPress drafts.

    Raises `agents.wordpress.client.WordPressConfigurationError` (handled
    in `app.api.errors`, translated to a 503) when
    `WORDPRESS_SITE_URL`/`WORDPRESS_USERNAME`/`WORDPRESS_APP_PASSWORD`
    are not set in `.env` — Sprint 4A, Increment 3.
    """
    return WordPressCMSPublisher(get_settings())


def get_media_storage() -> MediaStorage:
    """Return the storage backend used to save/read/delete MediaAsset files.

    Sprint 4A, Increment 7 (see docs/adr/ADR-007-media-assets.md). A
    Railway Volume in production, a plain local directory otherwise — see
    `agents.storage.local_disk.LocalDiskMediaStorage`.
    """
    return LocalDiskMediaStorage(get_settings().media_storage_dir)


def hash_session_token(token: str) -> str:
    """Return the SHA-256 hex digest of a raw session token.

    Session tokens are already high-entropy random values
    (`secrets.token_urlsafe`), unlike passwords — a fast hash is enough
    here; Argon2's deliberate slowness would only cost CPU, not add real
    protection, for a value nobody is trying to brute-force guess.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_current_session(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> SessionEntity:
    """Resolve the current request's `Session` from its cookie, or reject it."""
    if session_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    session = uow.sessions.get_by_token_hash(hash_session_token(session_token))
    if session is None or session.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return session


def get_current_user(
    session: SessionEntity = Depends(get_current_session),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> User:
    """Resolve the current request's authenticated `User`.

    The dependency every protected route declares — even where the route
    itself never reads the returned `User`, requiring this dependency is
    what rejects unauthenticated requests with a 401 before the route body
    runs at all.
    """
    user = uow.users.get_by_id(session.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
    return user
