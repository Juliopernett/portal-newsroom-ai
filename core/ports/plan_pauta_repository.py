"""Port for PlanPauta persistence.

`delete` exists for the same reason it does on `core.ports.gasto_repository`
— an operator retiring a plan from the catalog removes it outright, there
is no history that references a `PlanPauta` by id.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.plan_pauta import PlanPauta


class PlanPautaRepository(Protocol):
    """Contract for storing and retrieving `PlanPauta` entities."""

    def save(self, plan: PlanPauta) -> None:
        """Persist `plan`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> PlanPauta | None:
        """Return the `PlanPauta` identified by `id`, or `None`."""
        ...

    def list_all(self) -> list[PlanPauta]:
        """Return every `PlanPauta`, ordered by `orden` then `nombre`."""
        ...

    def delete(self, id: str) -> None:
        """Remove the `PlanPauta` row identified by `id` — a no-op if it does not exist."""
        ...
