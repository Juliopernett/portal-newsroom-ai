"""Port for AIConfiguracion persistence.

`get`, not `get_by_id` — this is a singleton (see
`core.entities.ai_configuracion.ID_UNICO`), same shape as
`core.ports.identidad_comercial_repository.IdentidadComercialRepository`.
No `list_all`/`delete` — nothing in this sprint's scope needs more than one
row.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.ai_configuracion import AIConfiguracion


class AIConfiguracionRepository(Protocol):
    """Contract for storing and retrieving the one `AIConfiguracion` row."""

    def get(self) -> AIConfiguracion | None:
        """Return the configured `AIConfiguracion`, or `None` if never set."""
        ...

    def save(self, configuracion: AIConfiguracion) -> None:
        """Persist `configuracion`, creating or replacing the singleton row."""
        ...
