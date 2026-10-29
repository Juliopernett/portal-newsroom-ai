"""Port for Source persistence (Sprint Fuentes, 2026-10-29)."""

from __future__ import annotations

from typing import Protocol

from core.entities.source import Source


class SourceRepository(Protocol):
    """Contract for storing and retrieving configured Radar `Source`s."""

    def save(self, entity: Source) -> None:
        """Persist `entity`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> Source | None:
        """Return the `Source` identified by `id`, or `None` if not found."""
        ...

    def list_all(self) -> list[Source]:
        """Return every configured `Source`, highest priority first, then by name."""
        ...
