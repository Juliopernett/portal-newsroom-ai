"""HTTP schemas for DestinoPublicacion.

Sprint 4A, Increment 3 (see docs/adr/ADR-006-multichannel-publication.md).
`DestinoPublicacionCreate` only accepts `canal` — every destino is
created `PENDIENTE`, matching the entity's own default; there is no way
to create one already `PUBLICADO`/`FALLIDO`/`CANCELADO` directly, the
same discipline `PublicationRequestCreate` already applies to `estado`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.entities.destino_publicacion import CanalPublicacion, EstadoDestino


class DestinoPublicacionCreate(BaseModel):
    """Request body for `POST /publication-requests/{id}/destinos`."""

    canal: CanalPublicacion


class DestinoPublicacionOut(BaseModel):
    """Response body for a `DestinoPublicacion`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    publication_request_id: str
    canal: CanalPublicacion
    estado: EstadoDestino
    wp_post_id: str | None
    wp_url: str | None
    url_publicacion: str | None
    registrado_por_user_id: str | None
    fecha_publicacion: datetime | None
    ultimo_error: str | None
