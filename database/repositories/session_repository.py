"""SQLAlchemy adapter for `core.ports.session_repository.SessionRepository`.

Translates between `core.entities.session.Session` (domain) and
`database.models.session.SessionModel` (ORM). The domain never sees this
module.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as SqlAlchemySession

from core.entities.session import Session
from database.models.session import SessionModel


def _to_model(session: Session) -> SessionModel:
    return SessionModel(
        id=session.id,
        user_id=session.user_id,
        token_hash=session.token_hash,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


def _aware(value: datetime) -> datetime:
    """Re-attach UTC tzinfo SQLite drops on round trip (Postgres does not)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _to_domain(model: SessionModel) -> Session:
    return Session(
        id=model.id,
        user_id=model.user_id,
        token_hash=model.token_hash,
        created_at=_aware(model.created_at),
        expires_at=_aware(model.expires_at),
    )


class SqlAlchemySessionRepository:
    """`SessionRepository` implemented on top of a SQLAlchemy `Session`."""

    def __init__(self, session: SqlAlchemySession) -> None:
        self._session = session

    def save(self, session: Session) -> None:
        """Persist `session`, creating or updating it as needed."""
        self._session.merge(_to_model(session))

    def get_by_token_hash(self, token_hash: str) -> Session | None:
        """Return the `Session` identified by `token_hash`, or `None`."""
        stmt = select(SessionModel).where(SessionModel.token_hash == token_hash)
        model = self._session.execute(stmt).scalar_one_or_none()
        return _to_domain(model) if model is not None else None

    def delete(self, id: str) -> None:
        """Remove the `Session` identified by `id` — how logout works."""
        model = self._session.get(SessionModel, id)
        if model is not None:
            self._session.delete(model)
