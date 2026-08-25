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

from pydantic import BaseModel, ConfigDict, Field

from core.entities.destino_publicacion import CanalPublicacion
from core.entities.publication_request import EstadoPreparacionIA, PublicationRequestStatus

# security audit 2026-08-20, L1 — generous enough for any real solicitud
# (`texto` is a social-post caption, not an article body), but bounded so
# an oversized body doesn't reach the PDF renderer or the database
# unchecked. The entity itself (`core.entities.publication_request`) only
# checks non-empty; this is the size cap, kept at the HTTP boundary.
_TEXTO_MAX = 5000
_TITULO_MAX = 300
_OBSERVACIONES_MAX = 2000


class PublicationRequestCreate(BaseModel):
    """Request body for `POST /publication-requests`."""

    pauta_id: str | None = None
    client_id: str | None = None
    titulo: str | None = Field(default=None, max_length=_TITULO_MAX)
    texto: str = Field(max_length=_TEXTO_MAX)
    prioridad_manual: bool = False
    observaciones: str | None = Field(default=None, max_length=_OBSERVACIONES_MAX)
    # Pre-marcar destinos al registrar (2026-08-21): el operador ya sabe a
    # qué canales va la publicación, así que los crea de una vez como
    # DestinoPublicacion PENDIENTE — ahorra el viaje de vuelta a "Agregar
    # destino" por cada canal antes de poder pegar los enlaces al
    # confirmar. Opcional y sin duplicados por diseño de `canal` en
    # DestinoPublicacion; una solicitud sin canales se comporta como hoy.
    canales: list[CanalPublicacion] = Field(default_factory=list)


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

    titulo: str | None = Field(default=None, max_length=_TITULO_MAX)
    texto: str | None = Field(default=None, max_length=_TEXTO_MAX)
    prioridad_manual: bool | None = None


class PublicationRequestOut(BaseModel):
    """Response body for a `PublicationRequest`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    pauta_id: str | None
    client_id: str | None
    fecha_recepcion: datetime
    titulo: str | None
    texto: str
    estado: PublicationRequestStatus
    prioridad_manual: bool
    observaciones: str | None
    fecha_cierre: datetime | None
    # --- Preparación editorial con IA (Sprint 2026-08-21) — solo lectura,
    # nunca fijados por el cliente; ver PublicationRequestCreate/Update. ---
    contenido_editorial: str | None
    entradilla_editorial: str | None
    titulo_editorial: str | None
    categoria_editorial: str | None
    etiquetas_editorial: tuple[str, ...] | None
    slug_editorial: str | None
    meta_titulo_editorial: str | None
    meta_descripcion_editorial: str | None
    frase_clave_editorial: str | None
    preparacion_ia_estado: EstadoPreparacionIA
    preparacion_ia_error: str | None
