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


class DestinoPublicacionConfirmarPublicacion(BaseModel):
    """Request body for `POST .../destinos/{destino_id}/confirmar-publicacion`
    (Sprint 4A, Increment 4).

    `url_publicacion` is required for `FACEBOOK`/`INSTAGRAM` (the entity
    itself rejects `PUBLICADO` without it for those canales — see
    `core.entities.destino_publicacion`); WordPress already has `wp_url`
    from `crear-borrador-wordpress` and does not need one here.
    `meta_post_id` is set only when the operator picked the post from
    "elegir de posts recientes" — a manually-typed link leaves it unset.
    """

    url_publicacion: str | None = None
    meta_post_id: str | None = None


class DestinoPublicacionCorregirEnlace(BaseModel):
    """Request body for `PATCH .../destinos/{destino_id}/corregir-enlace`.

    Fixes a data-entry mistake on an already-`PUBLICADO` destino (e.g. the
    wrong Instagram link pasted while confirming several back-to-back) —
    see `core.services.destino_publicacion_service.corregir_enlace`. Only
    the field matching the destino's own canal is meaningful; the entity's
    own validation rejects the other one.
    """

    wp_url: str | None = None
    url_publicacion: str | None = None
    meta_post_id: str | None = None


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
    meta_post_id: str | None
    registrado_por_user_id: str | None
    fecha_publicacion: datetime | None
    ultimo_error: str | None
