"""Unit tests for get_current_session/get_current_user, called directly.

Both are plain functions once you have a `UnitOfWork` — no need to go
through a FastAPI `TestClient` to exercise the edge cases (forged token,
expired session, orphaned session) that a full login flow never
naturally produces.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database.models  # noqa: F401  (registers tables on Base.metadata)
from app.api.dependencies import get_current_session, get_current_user, hash_session_token
from core.entities.session import Session as SessionEntity
from core.entities.user import User
from database.base import Base
from database.unit_of_work import SqlAlchemyUnitOfWork
from security.password_hasher import Argon2IdPasswordHasher


@pytest.fixture
def uow() -> Iterator[SqlAlchemyUnitOfWork]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work


def _seed_user_and_session(uow: SqlAlchemyUnitOfWork, **session_overrides: object) -> str:
    """Persist a User and a valid Session for it, return the raw (unhashed) token."""
    user = User(
        email="editor@portalvallenato.com",
        password_hash=Argon2IdPasswordHasher().hash("whatever"),
        nombre="Editor de Turno",
    )
    uow.users.save(user)
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "user_id": user.id,
        "token_hash": hash_session_token("raw-token"),
        "created_at": now,
        "expires_at": now + timedelta(days=7),
    }
    defaults.update(session_overrides)
    uow.sessions.save(SessionEntity(**defaults))
    uow.commit()
    return "raw-token"


def test_get_current_session_rejects_a_missing_cookie(uow: SqlAlchemyUnitOfWork) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_current_session(session_token=None, uow=uow)

    assert exc_info.value.status_code == 401


def test_get_current_session_rejects_a_forged_token(uow: SqlAlchemyUnitOfWork) -> None:
    _seed_user_and_session(uow)

    with pytest.raises(HTTPException) as exc_info:
        get_current_session(session_token="not-the-real-token", uow=uow)

    assert exc_info.value.status_code == 401


def test_get_current_session_rejects_an_expired_session(uow: SqlAlchemyUnitOfWork) -> None:
    now = datetime.now(UTC)
    token = _seed_user_and_session(
        uow, created_at=now - timedelta(days=2), expires_at=now - timedelta(hours=1)
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_session(session_token=token, uow=uow)

    assert exc_info.value.status_code == 401


def test_get_current_session_accepts_a_valid_token(uow: SqlAlchemyUnitOfWork) -> None:
    token = _seed_user_and_session(uow)

    session = get_current_session(session_token=token, uow=uow)

    assert session.token_hash == hash_session_token(token)


def test_get_current_user_rejects_a_session_with_no_matching_user(
    uow: SqlAlchemyUnitOfWork,
) -> None:
    now = datetime.now(UTC)
    orphan_session = SessionEntity(
        user_id="no-such-user",
        token_hash="irrelevant",
        created_at=now,
        expires_at=now + timedelta(days=7),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(session=orphan_session, uow=uow)

    assert exc_info.value.status_code == 401


def test_get_current_user_returns_the_matching_user(uow: SqlAlchemyUnitOfWork) -> None:
    token = _seed_user_and_session(uow)
    session = get_current_session(session_token=token, uow=uow)

    user = get_current_user(session=session, uow=uow)

    assert user.email == "editor@portalvallenato.com"
