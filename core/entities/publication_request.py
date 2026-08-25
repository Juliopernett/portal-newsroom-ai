"""Domain entity: a publication request received from a commercial Client.

What arrives over WhatsApp from a manager, artist, promoter or business
owner: text today, attachments in a later sprint (see docs/roadmap).
Deliberately scoped to commercial content only — organic content stays
entirely inside Discovery (`core.entities.news_candidate.NewsCandidate`)
and never becomes a `PublicationRequest`; the two never converge in a
shared entity, see Sprint 3B domain discovery.

A request can arrive before anyone knows which `Pauta` it belongs to:
`pauta_id` is optional while `estado` is `RECIBIDA` or `CANCELADA`, and
becomes mandatory the moment a request moves to `ACEPTADA` (Sprint 3B.1
domain adjustment) — matching how triage actually happens: an operator
links a request to a `Client`'s `Pauta` before accepting it, never before.

`titulo` and `fecha_cierre` are Sprint 4A additions (see
docs/adr/ADR-006-multichannel-publication.md) — Increment 1 of that
ADR's rollout.

`client_id` is a separate, optional reference to the `Client` the request
came from — independent of `pauta_id`. A request received before its
`Pauta` is known (or from a client with no vigente `Pauta` yet) would
otherwise carry no identity at all in the working queue; this lets an
operator record who sent it without forcing a `Pauta` link at intake.
Unlike `pauta_id`, nothing in this entity ever requires `client_id` — it
is informational only, never validated against `pauta_id`'s own client
once a `Pauta` is linked.

**`PUBLICADA` retired in Increment 4.** `estado` now describes only
intake triage (`RECIBIDA` → `ACEPTADA` → `CANCELADA`) — the same
deliberately simple role `ArticleStatus` plays for `Article` (see
ADR-002). Whether a request is actually done publishing lives entirely
in its `DestinoPublicacion`s, via the derived
`core.services.destino_publicacion_service.esta_completa` — never in
`estado`. `ACEPTADA` is the state a request moves to once it starts
being worked (the old single-click "Publicar" flow now transitions here
instead of to a since-removed `PUBLICADA`, see
`core.services.publication_request_service.aceptar`); `pauta_id` being
required at that point is the same invariant `PUBLICADA` used to also
enforce, preserved by keeping `ACEPTADA` in
`_ESTADOS_CON_PAUTA_OBLIGATORIA`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class PublicationRequestStatus(StrEnum):
    """Lifecycle of a commercial publication request — triage only, see module docstring."""

    RECIBIDA = "recibida"
    ACEPTADA = "aceptada"
    CANCELADA = "cancelada"


class EstadoPreparacionIA(StrEnum):
    """Whether the automatic editorial rewrite (Sprint — preparación editorial con
    IA, 2026-08-21) has run for this solicitud.

    `PENDIENTE` is the default for every solicitud, old and new alike —
    `crear_borrador_wordpress` is the only place that ever moves it forward.
    `FALLIDO` is not a dead end: the WordPress draft still gets created with
    the raw `texto` when the AI step fails (see
    `core.services.wordpress_publication_service.preparar_y_crear_borrador`)
    — a caída de la IA nunca debe bloquear el flujo de WordPress.
    """

    PENDIENTE = "pendiente"
    PROCESADO = "procesado"
    FALLIDO = "fallido"


_ESTADOS_CON_PAUTA_OBLIGATORIA: frozenset[PublicationRequestStatus] = frozenset(
    {PublicationRequestStatus.ACEPTADA}
)


@dataclass(frozen=True, slots=True, kw_only=True)
class PublicationRequest:
    """A publication request, optionally tied to a Client's Pauta.

    `pauta_id` is required once `estado` is `ACEPTADA`, and optional
    otherwise (`RECIBIDA`, `CANCELADA`).
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    pauta_id: str | None = None
    client_id: str | None = None
    fecha_recepcion: datetime = field(default_factory=lambda: datetime.now(UTC))
    titulo: str | None = None
    texto: str
    estado: PublicationRequestStatus = PublicationRequestStatus.RECIBIDA
    prioridad_manual: bool = False
    observaciones: str | None = None
    fecha_cierre: datetime | None = None
    # --- Preparación editorial con IA (Sprint 2026-08-21) ---
    # `texto` above stays forever the untouched contenido_original; these
    # fields hold the IA's proposal, kept in a clean separate namespace so
    # nothing here ever overwrites what the client actually sent. All
    # populated together, only when `preparacion_ia_estado` becomes
    # PROCESADO — see `core.services.editorial_ai_service`.
    contenido_editorial: str | None = None
    entradilla_editorial: str | None = None
    titulo_editorial: str | None = None
    categoria_editorial: str | None = None
    etiquetas_editorial: tuple[str, ...] | None = None
    slug_editorial: str | None = None
    # SEO real (Sprint 2026-08-25) — feed Yoast SEO's own fields
    # (_yoast_wpseo_title/_metadesc/_focuskw) instead of leaving every
    # AI-prepared draft with Yoast's "necesita mejorar" score.
    meta_titulo_editorial: str | None = None
    meta_descripcion_editorial: str | None = None
    frase_clave_editorial: str | None = None
    preparacion_ia_estado: EstadoPreparacionIA = EstadoPreparacionIA.PENDIENTE
    preparacion_ia_error: str | None = None

    def __post_init__(self) -> None:
        if self.pauta_id == "":
            raise ValueError(
                "pauta_id must not be an empty string — use None if not linked to a Pauta yet"
            )
        if self.client_id == "":
            raise ValueError(
                "client_id must not be an empty string — use None if not set"
            )
        if not self.texto:
            raise ValueError("texto must not be empty")
        if self.titulo == "":
            raise ValueError("titulo must not be an empty string — use None if not set yet")
        if self.estado in _ESTADOS_CON_PAUTA_OBLIGATORIA and self.pauta_id is None:
            raise ValueError(f"pauta_id is required when estado is {self.estado.value!r}")
        if (
            self.preparacion_ia_estado == EstadoPreparacionIA.PROCESADO
            and self.contenido_editorial is None
        ):
            raise ValueError(
                "contenido_editorial is required when preparacion_ia_estado is 'procesado'"
            )
        if (
            self.preparacion_ia_estado == EstadoPreparacionIA.FALLIDO
            and self.preparacion_ia_error is None
        ):
            raise ValueError(
                "preparacion_ia_error is required when preparacion_ia_estado is 'fallido'"
            )
