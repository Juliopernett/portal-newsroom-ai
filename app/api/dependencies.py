"""FastAPI dependency injection for the internal API.

The only place in `app/api/` that touches `database.engine`/
`database.unit_of_work` directly — every route handler depends on
`core.ports.unit_of_work.UnitOfWork` (the abstraction), never on
`SqlAlchemyUnitOfWork` (the adapter), so tests can override this one
function to point at a throwaway database instead.
"""

from __future__ import annotations

from collections.abc import Iterator

from core.ports.unit_of_work import UnitOfWork
from database.engine import get_session_factory
from database.unit_of_work import SqlAlchemyUnitOfWork


def get_unit_of_work() -> Iterator[UnitOfWork]:
    """Yield a `UnitOfWork` scoped to a single request.

    Commit is never implicit — a route handler that doesn't call
    `uow.commit()` gets a clean rollback when the request ends, the same
    "no commit means nothing happened" discipline `SqlAlchemyUnitOfWork`
    already guarantees.
    """
    with SqlAlchemyUnitOfWork(get_session_factory()) as uow:
        yield uow
