"""Port for atomic, multi-repository transactions.

An `ABC`, not a `Protocol` — unlike every other port in `core/ports/` —
because `__enter__`/`__exit__` share real, non-trivial logic every adapter
needs identically (always roll back on exit unless `commit()` was already
called), the exact carve-out docs/CODING_STANDARDS.md allows for ports
that need shared behavior in a base class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType

from core.ports.client_repository import ClientRepository
from core.ports.pauta_repository import PautaRepository
from core.ports.publication_request_repository import PublicationRequestRepository
from core.ports.session_repository import SessionRepository
from core.ports.user_repository import UserRepository


class UnitOfWork(ABC):
    """Groups repository operations into a single atomic transaction.

    Concrete adapters (`database.unit_of_work.SqlAlchemyUnitOfWork`) open a
    transaction on `__enter__` and expose `clients`/`pautas`/
    `publication_requests`/`users`/`sessions` bound to it. Exiting the
    `with` block always rolls back unless `commit()` was called explicitly
    first — the same discipline regardless of what happened inside the
    block, so callers never have to remember to clean up after an
    exception.
    """

    clients: ClientRepository
    pautas: PautaRepository
    publication_requests: PublicationRequestRepository
    users: UserRepository
    sessions: SessionRepository

    @abstractmethod
    def __enter__(self) -> UnitOfWork:
        """Open a transaction and bind `clients`/`pautas`/`publication_requests` to it."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.rollback()

    @abstractmethod
    def commit(self) -> None:
        """Persist every change made through this unit of work."""

    @abstractmethod
    def rollback(self) -> None:
        """Discard every change made through this unit of work."""
