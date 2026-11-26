"""Port for ColoresMarca persistence — a singleton, hence `get`."""

from __future__ import annotations

from typing import Protocol

from core.entities.colores_marca import ColoresMarca


class ColoresMarcaRepository(Protocol):
    """Contract for storing and retrieving the one `ColoresMarca` row."""

    def get(self) -> ColoresMarca | None:
        """Return the saved colours, or `None` if nobody changed them."""
        ...

    def save(self, colores: ColoresMarca) -> None:
        """Persist `colores`, creating or replacing the singleton row."""
        ...
