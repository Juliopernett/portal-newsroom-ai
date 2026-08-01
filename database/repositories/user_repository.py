"""SQLAlchemy adapter for `core.ports.user_repository.UserRepository`.

Translates between `core.entities.user.User` (domain) and
`database.models.user.UserModel` (ORM). The domain never sees this
module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.user import User
from database.models.user import UserModel


def _to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        email=user.email,
        password_hash=user.password_hash,
        nombre=user.nombre,
        created_at=user.created_at,
    )


def _to_domain(model: UserModel) -> User:
    created_at = model.created_at
    if created_at.tzinfo is None:
        # SQLite drops tzinfo on round trip (Postgres does not) — see
        # database.repositories.publication_request_repository for the
        # same fix, applied there first.
        created_at = created_at.replace(tzinfo=UTC)
    return User(
        id=model.id,
        email=model.email,
        password_hash=model.password_hash,
        nombre=model.nombre,
        created_at=created_at,
    )


class SqlAlchemyUserRepository:
    """`UserRepository` implemented on top of a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, user: User) -> None:
        """Persist `user`, creating or updating it as needed."""
        self._session.merge(_to_model(user))

    def get_by_id(self, id: str) -> User | None:
        """Return the `User` identified by `id`, or `None` if not found."""
        model = self._session.get(UserModel, id)
        return _to_domain(model) if model is not None else None

    def get_by_email(self, email: str) -> User | None:
        """Return the `User` identified by `email`, or `None` if not found."""
        stmt = select(UserModel).where(UserModel.email == email)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_domain(model) if model is not None else None
