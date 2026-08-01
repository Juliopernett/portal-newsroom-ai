"""SQLAlchemy adapter for `core.ports.unit_of_work.UnitOfWork`.

Owns a single `Session` for the lifetime of the `with` block, wires the
three concrete repositories to it, and commits/rolls back that one
session — the transaction boundary is the `with` block, nothing else.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker

from core.ports.unit_of_work import UnitOfWork
from database.repositories.client_repository import SqlAlchemyClientRepository
from database.repositories.pauta_repository import SqlAlchemyPautaRepository
from database.repositories.publication_request_repository import (
    SqlAlchemyPublicationRequestRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Groups `Client`/`Pauta`/`PublicationRequest` repositories in one transaction."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.clients = SqlAlchemyClientRepository(self._session)
        self.pautas = SqlAlchemyPautaRepository(self._session)
        self.publication_requests = SqlAlchemyPublicationRequestRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        super().__exit__(exc_type, exc_value, traceback)
        assert self._session is not None
        self._session.close()
        self._session = None

    def commit(self) -> None:
        """Commit the current session's transaction."""
        assert self._session is not None
        self._session.commit()

    def rollback(self) -> None:
        """Roll back the current session's transaction."""
        assert self._session is not None
        self._session.rollback()
