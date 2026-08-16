"""Port for OtroIngreso persistence.

`delete` exists here for the same reason it exists on
`core.ports.gasto_repository.GastoRepository` — an OtroIngreso really does
go away when an operator fixes a data-entry mistake (wrong amount,
duplicate row).
"""

from __future__ import annotations

from typing import Protocol

from core.entities.otro_ingreso import OtroIngreso


class OtroIngresoRepository(Protocol):
    """Contract for storing and retrieving `OtroIngreso` entities."""

    def save(self, ingreso: OtroIngreso) -> None:
        """Persist `ingreso`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> OtroIngreso | None:
        """Return the `OtroIngreso` identified by `id`, or `None`."""
        ...

    def list_all(self) -> list[OtroIngreso]:
        """Return every `OtroIngreso` — the registro screen and the rentabilidad report."""
        ...

    def delete(self, id: str) -> None:
        """Remove the `OtroIngreso` row identified by `id` — a no-op if it does not exist."""
        ...
