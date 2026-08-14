"""Port for Gasto persistence.

`delete` exists here for the same reason it exists on
`core.ports.media_asset_repository.MediaAssetRepository` — a Gasto really
does go away when an operator fixes a data-entry mistake (wrong amount,
duplicate row), unlike `DestinoPublicacion`, which only ever moves to a
terminal state.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.gasto import Gasto


class GastoRepository(Protocol):
    """Contract for storing and retrieving `Gasto` entities."""

    def save(self, gasto: Gasto) -> None:
        """Persist `gasto`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> Gasto | None:
        """Return the `Gasto` identified by `id`, or `None`."""
        ...

    def list_all(self) -> list[Gasto]:
        """Return every `Gasto` — the registro screen and the rentabilidad report."""
        ...

    def delete(self, id: str) -> None:
        """Remove the `Gasto` row identified by `id` — a no-op if it does not exist."""
        ...
