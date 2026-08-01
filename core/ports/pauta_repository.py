"""Port for Pauta persistence.

`list_all` exists because `core.services.pauta_service.PautaService.pautas_por_vencer`
concretely needs "every Pauta in the system" to answer "which clients are
about to expire" — not a hypothetical query, the one the domain already
calls.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.pauta import Pauta


class PautaRepository(Protocol):
    """Contract for storing and retrieving `Pauta` entities."""

    def save(self, pauta: Pauta) -> None:
        """Persist `pauta`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> Pauta | None:
        """Return the `Pauta` identified by `id`, or `None` if not found."""
        ...

    def list_all(self) -> list[Pauta]:
        """Return every `Pauta` — the input `pautas_por_vencer` needs."""
        ...
