"""Port for persisting the last metrics capture per destino."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from core.entities.metrica_publicacion import MetricaPublicacion


class MetricaPublicacionRepository(Protocol):
    """Contract for storing and retrieving `MetricaPublicacion` entities."""

    def save(self, metrica: MetricaPublicacion) -> None:
        """Create or replace the capture for `metrica.destino_id`."""
        ...

    def list_by_destino_ids(self, destino_ids: Iterable[str]) -> list[MetricaPublicacion]:
        """Return the saved captures for the given destinos (missing ones omitted)."""
        ...
