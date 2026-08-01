"""Port for persistence and editorial history.

Implemented by adapters in `database/repositories/`. Backs deduplication
("has this content been processed before?") and the editorial history
required by docs/PROJECT_RULES.md. Generic over the entity type so it can
be reused once concrete domain entities exist (see docs/ROADMAP.md).
"""

from __future__ import annotations

from typing import Protocol, TypeVar

# Contravariant: today `T` is only ever consumed (as a `save()` argument),
# never produced. If a `get() -> T` method is added once concrete entities
# exist (see docs/ROADMAP.md), T will need to become invariant again —
# mypy --strict will flag that mismatch when it happens.
T = TypeVar("T", contravariant=True)


class Repository(Protocol[T]):
    """Contract for storing and retrieving domain entities."""

    def save(self, entity: T) -> None:
        """Persist `entity`, creating or updating it as needed."""
        ...

    def exists(self, reference: str) -> bool:
        """Return whether an entity identified by `reference` was already stored.

        This is the primary hook used to avoid processing duplicate news.
        """
        ...
