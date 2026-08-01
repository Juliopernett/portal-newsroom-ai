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
