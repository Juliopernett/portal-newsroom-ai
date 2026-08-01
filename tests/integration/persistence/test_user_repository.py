"""Integration tests: SqlAlchemyUserRepository against a real SQLite schema."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.entities.user import User
from database.repositories.user_repository import SqlAlchemyUserRepository


def _user(**overrides: object) -> User:
    defaults: dict[str, object] = {
        "email": "editor@portalvallenato.com",
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$fake",
        "nombre": "Editor de Turno",
    }
    defaults.update(overrides)
    return User(**defaults)


def test_save_and_get_by_id_round_trips_a_user(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)
    user = _user()

    repository.save(user)
    session.commit()

    assert repository.get_by_id(user.id) == user


def test_get_by_id_returns_none_when_not_found(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)

    assert repository.get_by_id("no-existe") is None


def test_get_by_email_finds_the_matching_user(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)
    user = _user(email="alguien@portalvallenato.com")
    repository.save(user)
    session.commit()

    assert repository.get_by_email("alguien@portalvallenato.com") == user


def test_get_by_email_returns_none_when_not_found(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)

    assert repository.get_by_email("no-existe@portalvallenato.com") is None


def test_save_rejects_a_duplicate_email(session: Session) -> None:
    repository = SqlAlchemyUserRepository(session)
    repository.save(_user(email="duplicado@portalvallenato.com"))
    session.commit()

    repository.save(_user(email="duplicado@portalvallenato.com"))
    with pytest.raises(IntegrityError):
        session.commit()
