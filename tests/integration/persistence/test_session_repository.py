"""Integration tests: SqlAlchemySessionRepository against a real SQLite schema."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as SqlAlchemySession

from core.entities.session import Session
from core.entities.user import User
from database.repositories.session_repository import SqlAlchemySessionRepository
from database.repositories.user_repository import SqlAlchemyUserRepository


def _create_user(session: SqlAlchemySession, **overrides: object) -> User:
    """Persist a User so FK-constrained Session tests have a real parent.

    Flushes immediately: `UserModel`/`SessionModel` have no ORM-level
    `relationship()` between them (mapped as plain FK columns, matching
    the rest of `database/models/`), so SQLAlchemy's unit-of-work has no
    way to order their inserts within one flush — without this, `sessions`
    (alphabetically first) can be inserted before `users`, failing the FK
    constraint. Production code never hits this: every route commits one
    entity at a time.
    """
    defaults: dict[str, object] = {
        "email": "editor@portalvallenato.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fake",
        "nombre": "Editor de Turno",
    }
    defaults.update(overrides)
    user = User(**defaults)
    SqlAlchemyUserRepository(session).save(user)
    session.flush()
    return user


def _session_entity(user_id: str, **overrides: object) -> Session:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "user_id": user_id,
        "token_hash": "abc123",
        "created_at": now,
        "expires_at": now + timedelta(days=7),
    }
    defaults.update(overrides)
    return Session(**defaults)


def test_save_and_get_by_token_hash_round_trips_a_session(session: SqlAlchemySession) -> None:
    user = _create_user(session)
    repository = SqlAlchemySessionRepository(session)
    entity = _session_entity(user.id, token_hash="a-real-looking-hash")

    repository.save(entity)
    session.commit()

    assert repository.get_by_token_hash("a-real-looking-hash") == entity


def test_get_by_token_hash_returns_none_when_not_found(session: SqlAlchemySession) -> None:
    repository = SqlAlchemySessionRepository(session)

    assert repository.get_by_token_hash("no-existe") is None


def test_delete_removes_the_session(session: SqlAlchemySession) -> None:
    user = _create_user(session)
    repository = SqlAlchemySessionRepository(session)
    entity = _session_entity(user.id, token_hash="to-delete")
    repository.save(entity)
    session.commit()

    repository.delete(entity.id)
    session.commit()

    assert repository.get_by_token_hash("to-delete") is None


def test_delete_is_a_noop_when_the_session_does_not_exist(session: SqlAlchemySession) -> None:
    repository = SqlAlchemySessionRepository(session)

    repository.delete("no-existe")  # must not raise
    session.commit()
