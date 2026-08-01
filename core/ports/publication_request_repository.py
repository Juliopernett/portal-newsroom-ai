"""Port for PublicationRequest persistence.

`list_by_pauta_id` exists because every quota calculation in
`core.services.pauta_service.PautaService` (`publicaciones_consumidas`,
`publicaciones_restantes`, `cuota_agotada`) needs exactly that sequence —
not a hypothetical query, the one the domain already calls. `list_all`
exists because `GET /publication-requests` (Sprint 3D, internal UI) is
the daily "qué publicar hoy" queue — `estado` is optional because the UI
filters to `RECIBIDA` by default; without the filter it would have to
fetch everything and discard most of it client-side for no reason.
"""

from __future__ import annotations

from typing import Protocol

from core.entities.publication_request import PublicationRequest, PublicationRequestStatus


class PublicationRequestRepository(Protocol):
    """Contract for storing and retrieving `PublicationRequest` entities."""

    def save(self, solicitud: PublicationRequest) -> None:
        """Persist `solicitud`, creating or updating it as needed."""
        ...

    def get_by_id(self, id: str) -> PublicationRequest | None:
        """Return the `PublicationRequest` identified by `id`, or `None`."""
        ...

    def list_by_pauta_id(self, pauta_id: str) -> list[PublicationRequest]:
        """Return every request linked to `pauta_id` — what PautaService needs."""
        ...

    def list_all(self, estado: PublicationRequestStatus | None = None) -> list[PublicationRequest]:
        """Return every request, optionally filtered to a single `estado`."""
        ...
