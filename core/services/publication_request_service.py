"""Domain service: state transitions a PublicationRequest needs.

Entities in `core/entities/` are immutable (`frozen=True`) — moving a
`PublicationRequest` forward in its lifecycle produces a new instance, it
never mutates the one passed in, the same discipline the rest of the
domain already follows (see `core.entities.pauta.Pauta`'s docstring).
"""

from __future__ import annotations

from dataclasses import replace

from core.entities.publication_request import PublicationRequest, PublicationRequestStatus


def mark_as_published(solicitud: PublicationRequest) -> PublicationRequest:
    """Return a copy of `solicitud` transitioned to `PUBLICADA`.

    Raises `ValueError` (via `PublicationRequest`'s own validation) if
    `solicitud.pauta_id` is `None` — `PUBLICADA` requires a `Pauta`.
    """
    return replace(solicitud, estado=PublicationRequestStatus.PUBLICADA)


def link_pauta(solicitud: PublicationRequest, pauta_id: str) -> PublicationRequest:
    """Return a copy of `solicitud` linked to `pauta_id`.

    Closes the Sprint 3B.1 gap: a request received without a Pauta
    (`origin` unknown at intake time) must be linkable later, before it
    can move to `ACEPTADA`/`PUBLICADA` — see docs/ux/sprint-3d5-ux-review.md.
    Does not change `estado`; a request stays `RECIBIDA` until it is
    explicitly published via `mark_as_published`.
    """
    return replace(solicitud, pauta_id=pauta_id)


def edit_solicitud(
    solicitud: PublicationRequest,
    *,
    texto: str | None = None,
    prioridad_manual: bool | None = None,
) -> PublicationRequest:
    """Return a copy of `solicitud` with `texto`/`prioridad_manual` corrected.

    Closes the Sprint UX 3.1 gap: the editorial queue offers an "Editar"
    action on a pending card but until now there was no way to fix a typo
    or toggle prioridad_manual after intake without recreating the
    request. Only a RECIBIDA request can be edited — once PUBLICADA, the
    published text is what actually went out, so editing it after the
    fact would make the record lie about what was posted.

    A field left as `None` keeps its current value — a partial update,
    the same convention `PublicationRequestUpdate` (the schema calling
    this) already uses.
    """
    if solicitud.estado != PublicationRequestStatus.RECIBIDA:
        raise ValueError(
            f"cannot edit a PublicationRequest once its estado is {solicitud.estado.value!r}"
        )
    cambios: dict[str, object] = {}
    if texto is not None:
        cambios["texto"] = texto
    if prioridad_manual is not None:
        cambios["prioridad_manual"] = prioridad_manual
    return replace(solicitud, **cambios)
