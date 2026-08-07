"""HTTP schemas for PublicationRequest.

`PublicationRequestCreate` never accepts `estado` — every request is
created `RECIBIDA`, matching the entity's own default (Sprint 3B.1); a
separate endpoint (`POST /publication-requests/{id}/publish`) is the only
way to move it forward, exposing `core.services.publication_request_service.aceptar`
(Sprint 4A, Increment 4 — replaces the retired `mark_as_published`)
rather than letting a client set an arbitrary state directly.

`titulo` (Sprint 4A, Increment 2) is optional on create and editable
while `RECIBIDA`, same as `texto`/`prioridad_manual` — see
`docs/adr/ADR-006-multichannel-publication.md`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.entities.publication_request import PublicationRequestStatus


class PublicationRequestCreate(BaseModel):
    """Request body for `POST /publication-requests`."""

    pauta_id: str | None = None
    titulo: str | None = None
    texto: str
    prioridad_manual: bool = False
    observaciones: str | None = None


class PublicationRequestLinkPauta(BaseModel):
    """Request body for `POST /publication-requests/{id}/link-pauta` (Sprint 3E)."""

    pauta_id: str


class PublicationRequestUpdate(BaseModel):
    """Request body for `PATCH /publication-requests/{id}` (Sprint UX 3.1;
    `titulo` added Sprint 4A Increment 2).

    A field left unset keeps its current value — a partial update, not a
    PUT. Only `titulo`, `texto` and `prioridad_manual` are editable this
    way; `pauta_id` already has its own endpoint (`link-pauta`) and
    `estado` is never settable directly (see `PublicationRequestCreate`'s
    docstring for why).
    """

    titulo: str | None = None
    texto: str | None = None
    prioridad_manual: bool | None = None


class PublicationRequestOut(BaseModel):
    """Response body for a `PublicationRequest`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    pauta_id: str | None
    fecha_recepcion: datetime
    titulo: str | None
    texto: str
    estado: PublicationRequestStatus
    prioridad_manual: bool
    observaciones: str | None
    fecha_cierre: datetime | None
