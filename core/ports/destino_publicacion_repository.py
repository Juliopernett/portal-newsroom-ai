"""Port for DestinoPublicacion persistence.

`list_by_publication_request_id` exists because every consumer of a
`PublicationRequest`'s destinos — `core.services.destino_publicacion_service.esta_completa`,
the eventual multi-destino UI (Increment 2) — needs exactly that
sequence, scoped to one solicitud, not a hypothetical query.

`list_all` (Sprint 4A, Increment 4) exists because the quota-by-completitud
cutover (`core.services.pauta_service.PautaService`,
`core.analytics.AnalyticsService`) needs every destino across every
solicitud to compute `esta_completa` per solicitud — the same shape
`PublicationRequestRepository.list_all` already has, for the same reason.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.destino_publicacion import DestinoPublicacion


class DestinoPublicacionRepository(Protocol):
    """Contract for storing and retrieving `DestinoPublicacion` entities."""

    def save(self, destino: DestinoPublicacion) -> None:
        """Persist `destino`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> DestinoPublicacion | None:
        """Return the `DestinoPublicacion` identified by `id`, or `None`."""
        ...

    def list_by_publication_request_id(
        self, publication_request_id: str
    ) -> list[DestinoPublicacion]:
        """Return every destino belonging to `publication_request_id`."""
        ...

    def list_all(self) -> list[DestinoPublicacion]:
        """Return every destino in the system."""
        ...

    def delete(self, id: str) -> None:
        """Remove the `DestinoPublicacion` identified by `id`.

        A no-op if no such destino exists. Reserved for destinos that
        turned out redundant (e.g. the WordPress placeholder every
        `PublicationRequest.publish` created before the multi-destino
        model existed, once a real Facebook/Instagram destino already
        covers the same solicitud) — never used to undo a genuine
        publication; see `core.services.destino_publicacion_service.
        puede_eliminarse_sin_afectar_completitud`, which every caller of
        this must check first.
        """
        ...
