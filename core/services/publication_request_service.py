"""Domain service: state transitions a PublicationRequest needs.

Entities in `core/entities/` are immutable (`frozen=True`) — moving a
`PublicationRequest` forward in its lifecycle produces a new instance, it
never mutates the one passed in, the same discipline the rest of the
domain already follows (see `core.entities.pauta.Pauta`'s docstring).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from core.entities.destino_publicacion import DestinoPublicacion
from core.entities.publication_request import (
    EstadoPreparacionIA,
    PublicationRequest,
    PublicationRequestStatus,
)
from core.services.destino_publicacion_service import esta_completa


def aceptar(solicitud: PublicationRequest) -> PublicationRequest:
    """Return a copy of `solicitud` transitioned to `ACEPTADA`.

    Sprint 4A, Increment 4 — replaces the retired `mark_as_published`.
    Raises `ValueError` (via `PublicationRequest`'s own validation) if
    `solicitud.pauta_id` is `None` — `ACEPTADA` requires a `Pauta`, the
    same invariant `PUBLICADA` used to enforce. Does not touch any
    `DestinoPublicacion` — the old single-click "Publicar" endpoint
    (`app.api.routers.publication_requests.publish_publication_request`)
    calls this and then separately creates/marks a WordPress destino, so
    that endpoint's behavior stays visible-unchanged to the operator.
    """
    return replace(solicitud, estado=PublicationRequestStatus.ACEPTADA)


def cancelar_solicitud(solicitud: PublicationRequest) -> PublicationRequest:
    """Return a copy of `solicitud` transitioned to `CANCELADA`.

    Closes a real gap: `PublicationRequestStatus.CANCELADA` existed on the
    entity since it was defined but nothing ever produced it — a request
    the client asked to cancel before it went out had no way to be closed
    out, and stayed stuck in the working queue indefinitely (2026-08-14).
    Only a still-RECIBIDA request can be cancelled, the same restriction
    `edit_solicitud` already applies and for the same reason: once
    ACEPTADA, distribution work may already be underway (see
    `core.services.destino_publicacion_service`), so cancelling at that
    point would hide in-progress work instead of describing a request
    stopped before anything started.
    """
    if solicitud.estado != PublicationRequestStatus.RECIBIDA:
        raise ValueError(
            f"cannot cancel a PublicationRequest once its estado is {solicitud.estado.value!r}"
        )
    return replace(solicitud, estado=PublicationRequestStatus.CANCELADA)


def link_pauta(solicitud: PublicationRequest, pauta_id: str) -> PublicationRequest:
    """Return a copy of `solicitud` linked to `pauta_id`.

    Closes the Sprint 3B.1 gap: a request received without a Pauta
    (`origin` unknown at intake time) must be linkable later, before it
    can move to `ACEPTADA` — see docs/ux/sprint-3d5-ux-review.md. Does
    not change `estado`; a request stays `RECIBIDA` until it is
    explicitly accepted via `aceptar`.
    """
    return replace(solicitud, pauta_id=pauta_id)


def edit_solicitud(
    solicitud: PublicationRequest,
    *,
    titulo: str | None = None,
    texto: str | None = None,
    prioridad_manual: bool | None = None,
) -> PublicationRequest:
    """Return a copy of `solicitud` with `titulo`/`texto`/`prioridad_manual` corrected.

    Closes the Sprint UX 3.1 gap: the editorial queue offers an "Editar"
    action on a pending card but until now there was no way to fix a typo
    or toggle prioridad_manual after intake without recreating the
    request. Only a RECIBIDA request can be edited — once ACEPTADA, work
    on distributing it may already be underway (see
    `core.services.destino_publicacion_service`), so editing the text at
    that point would make the record lie about what was actually sent out.

    `titulo` (Sprint 4A, Increment 2) follows the same partial-update
    convention as `texto`/`prioridad_manual`: a field left as `None` keeps
    its current value, the same convention `PublicationRequestUpdate`
    (the schema calling this) already uses. There is deliberately no way
    to clear a `titulo` back to `None` through this function — nothing in
    Increment 2 needs it, and `PublicationRequest.__post_init__` already
    rejects an empty string, so "no titulo yet" only ever happens at
    creation, never as an edit.

    Correcting `texto` (Sprint 2026-08-21) clears any AI editorial
    preparation already run and resets `preparacion_ia_estado` back to
    `PENDIENTE` — otherwise a later "Crear borrador" would either publish
    a rewrite of text the operator just replaced, or silently skip
    re-running the AI because `preparacion_ia_estado` still read
    `PROCESADO`. A `texto` correction that happens to match the current
    value exactly is not treated as a change, so it never wastes an
    already-successful preparation.
    """
    if solicitud.estado != PublicationRequestStatus.RECIBIDA:
        raise ValueError(
            f"cannot edit a PublicationRequest once its estado is {solicitud.estado.value!r}"
        )
    editada = replace(
        solicitud,
        titulo=titulo if titulo is not None else solicitud.titulo,
        texto=texto if texto is not None else solicitud.texto,
        prioridad_manual=prioridad_manual
        if prioridad_manual is not None
        else solicitud.prioridad_manual,
    )
    texto_cambio = texto is not None and texto != solicitud.texto
    if not texto_cambio:
        return editada
    return replace(
        editada,
        contenido_editorial=None,
        entradilla_editorial=None,
        titulo_editorial=None,
        categoria_editorial=None,
        etiquetas_editorial=None,
        slug_editorial=None,
        preparacion_ia_estado=EstadoPreparacionIA.PENDIENTE,
        preparacion_ia_error=None,
    )


def cerrar_si_completa(
    solicitud: PublicationRequest,
    destinos: Sequence[DestinoPublicacion],
    *,
    fecha_cierre: datetime | None = None,
) -> PublicationRequest:
    """Return `solicitud` with `fecha_cierre` stamped, the first time it completes.

    Sprint 4A, Increment 1 (see docs/adr/ADR-006-multichannel-publication.md,
    Decision 2), wired into the API in Increment 4. Idempotent: once
    `fecha_cierre` is already set, this returns `solicitud` unchanged
    regardless of `destinos` — closing is a one-time event, not a
    recomputed value, the same reasoning that keeps `Pauta.fecha_registro`
    an audit timestamp rather than a derived property. Called after every
    destino transition that could make a request complete (`publish`,
    `confirmar-publicacion`) in `app.api.routers.publication_requests`.
    """
    if solicitud.fecha_cierre is not None:
        return solicitud
    if not esta_completa(destinos):
        return solicitud
    return replace(solicitud, fecha_cierre=fecha_cierre or datetime.now(UTC))
