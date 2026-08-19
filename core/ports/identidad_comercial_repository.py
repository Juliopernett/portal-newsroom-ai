"""Port for IdentidadComercial persistence.

`get`, not `get_by_id` — this is a singleton (see
`core.entities.identidad_comercial.ID_UNICO`), the same shape difference
`core.ports.pauta_repository` would have if `Pauta` were ever singular.
There is no `list_all` or `delete`: nothing in this sprint's scope ever
needs more than one row or the absence of a row once configured.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.identidad_comercial import IdentidadComercial


class IdentidadComercialRepository(Protocol):
    """Contract for storing and retrieving the one `IdentidadComercial` row."""

    def get(self) -> IdentidadComercial | None:
        """Return the configured `IdentidadComercial`, or `None` if never set."""
        ...

    def save(self, identidad: IdentidadComercial) -> None:
        """Persist `identidad`, creating or replacing the singleton row."""
        ...
