"""Domain entity: one publication channel of a PublicationRequest.

Sprint 4A, Increment 1 (see docs/adr/ADR-006-multichannel-publication.md).
A `PublicationRequest` is no longer one publication in one implicit
channel — it distributes to zero or more `DestinoPublicacion`, one per
`canal`, each with its own independent lifecycle. This is the same role
`Publication`/`PublicationStatus` play for `Article` in
docs/product/DOMAIN_MODEL.md (see ADR-002), applied to the commercial
pillar instead of the editorial one — deliberately a separate entity, not
a shared one, per ADR-003's "organic and commercial never converge" rule.

WordPress-specific fields (`wp_post_id`, `wp_url`) and the manual-link
field (`url_publicacion`) are mutually exclusive by `canal` — see
`__post_init__`. `estado_completa`-style aggregation (whether a whole
`PublicationRequest` is done across all its destinos) is not this
entity's job; see `core.services.destino_publicacion_service.esta_completa`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import uuid4


class CanalPublicacion(StrEnum):
    """A publication channel a PublicationRequest can be distributed to."""

    WORDPRESS = "wordpress"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class EstadoDestino(StrEnum):
    """Lifecycle of a single DestinoPublicacion.

    `FALLIDO` is never a dead end — it must be retriable or manually
    cancellable, never a state that blocks a PublicationRequest from ever
    closing (see docs/adr/ADR-006-multichannel-publication.md, the
    "destinos fallidos" flow decision).
    """

    PENDIENTE = "pendiente"
    PUBLICADO = "publicado"
    FALLIDO = "fallido"
    CANCELADO = "cancelado"


_ESTADOS_TERMINALES: frozenset[EstadoDestino] = frozenset(
    {EstadoDestino.PUBLICADO, EstadoDestino.CANCELADO}
)

_CANALES_CON_CAMPOS_WORDPRESS: frozenset[CanalPublicacion] = frozenset({CanalPublicacion.WORDPRESS})
_CANALES_CON_URL_MANUAL: frozenset[CanalPublicacion] = frozenset(
    {CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class DestinoPublicacion:
    """One channel a PublicationRequest is (or was attempted to be) distributed to.

    `wp_post_id`/`wp_url` only ever apply to `canal=WORDPRESS`;
    `url_publicacion` only ever applies to `canal=FACEBOOK`/`INSTAGRAM` —
    each is rejected outside its matching `canal` in `__post_init__`, so an
    invalid combination can never be constructed.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    publication_request_id: str
    canal: CanalPublicacion
    estado: EstadoDestino = EstadoDestino.PENDIENTE
    wp_post_id: str | None = None
    wp_url: str | None = None
    url_publicacion: str | None = None
    registrado_por_user_id: str | None = None
    fecha_publicacion: datetime | None = None
    ultimo_error: str | None = None

    def __post_init__(self) -> None:
        if not self.publication_request_id:
            raise ValueError("publication_request_id must not be empty")
        if self.canal not in _CANALES_CON_CAMPOS_WORDPRESS and (
            self.wp_post_id is not None or self.wp_url is not None
        ):
            raise ValueError(
                f"wp_post_id/wp_url only apply to canal={CanalPublicacion.WORDPRESS.value!r}, "
                f"got canal={self.canal.value!r}"
            )
        if self.canal not in _CANALES_CON_URL_MANUAL and self.url_publicacion is not None:
            canales_validos = sorted(c.value for c in _CANALES_CON_URL_MANUAL)
            raise ValueError(
                f"url_publicacion only applies to canal in {canales_validos}, "
                f"got canal={self.canal.value!r}"
            )
        if self.estado == EstadoDestino.PUBLICADO and self.fecha_publicacion is None:
            raise ValueError("fecha_publicacion is required when estado is 'publicado'")
        if (
            self.estado == EstadoDestino.PUBLICADO
            and self.canal in _CANALES_CON_URL_MANUAL
            and self.url_publicacion is None
        ):
            raise ValueError(
                f"url_publicacion is required when estado is 'publicado' for "
                f"canal={self.canal.value!r} (Sprint 4A, Increment 4 — the operator "
                "must paste the link before confirming a Facebook/Instagram destino)"
            )

    @property
    def es_terminal(self) -> bool:
        """Return whether this destino is done — no further transition expected."""
        return self.estado in _ESTADOS_TERMINALES
