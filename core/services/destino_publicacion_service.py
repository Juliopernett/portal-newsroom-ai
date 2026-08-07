"""Domain service: state transitions a DestinoPublicacion needs, plus the
derived "is this PublicationRequest done" predicate.

Sprint 4A, Increment 1 (see docs/adr/ADR-006-multichannel-publication.md).
Entities in `core/entities/` are immutable (`frozen=True`) — every
transition here returns a new instance, never mutates the one passed in,
same discipline as `core.services.publication_request_service`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from core.entities.destino_publicacion import DestinoPublicacion, EstadoDestino


def marcar_publicado(
    destino: DestinoPublicacion,
    *,
    registrado_por_user_id: str | None = None,
    fecha_publicacion: datetime | None = None,
    wp_post_id: str | None = None,
    wp_url: str | None = None,
    url_publicacion: str | None = None,
) -> DestinoPublicacion:
    """Return a copy of `destino` transitioned to `PUBLICADO`.

    Allowed from `PENDIENTE` or `FALLIDO` (a retried failure can still
    succeed) — raises `ValueError` if `destino` is already terminal
    (`PUBLICADO`/`CANCELADO`). `fecha_publicacion` defaults to now (UTC)
    when not given, same convention as `Pauta.fecha_registro`'s own
    `default_factory`.
    """
    if destino.es_terminal:
        raise ValueError(
            f"cannot mark as publicado a destino already in a terminal estado "
            f"({destino.estado.value!r})"
        )
    return replace(
        destino,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=fecha_publicacion or datetime.now(UTC),
        registrado_por_user_id=registrado_por_user_id
        if registrado_por_user_id is not None
        else destino.registrado_por_user_id,
        wp_post_id=wp_post_id if wp_post_id is not None else destino.wp_post_id,
        wp_url=wp_url if wp_url is not None else destino.wp_url,
        url_publicacion=url_publicacion if url_publicacion is not None else destino.url_publicacion,
    )


def marcar_fallido(destino: DestinoPublicacion, *, error: str) -> DestinoPublicacion:
    """Return a copy of `destino` transitioned to `FALLIDO`, recording `error`.

    Raises `ValueError` if `destino` is already terminal — a destino that
    already succeeded or was cancelled cannot fail afterwards.
    """
    if destino.es_terminal:
        raise ValueError(
            f"cannot mark as fallido a destino already in a terminal estado "
            f"({destino.estado.value!r})"
        )
    return replace(destino, estado=EstadoDestino.FALLIDO, ultimo_error=error)


def cancelar(destino: DestinoPublicacion) -> DestinoPublicacion:
    """Return a copy of `destino` transitioned to `CANCELADO`.

    A `FALLIDO` destino is deliberately cancellable — it must never be a
    dead end that blocks a `PublicationRequest` from closing (see
    docs/adr/ADR-006-multichannel-publication.md). Raises `ValueError` if
    `destino` is already `PUBLICADO` — a real publication is never
    retroactively cancelled here (that would need an "archivar" concept,
    out of scope for Sprint 4A).
    """
    if destino.estado == EstadoDestino.PUBLICADO:
        raise ValueError("cannot cancel a destino already publicado")
    return replace(destino, estado=EstadoDestino.CANCELADO)


def esta_completa(destinos: Sequence[DestinoPublicacion]) -> bool:
    """Return whether a PublicationRequest's destinos add up to "complete".

    Derived, never stored (see docs/adr/ADR-006-multichannel-publication.md,
    Decision 2 — the only stored side effect of this becoming `True` is
    `PublicationRequest.fecha_cierre`, set once by
    `core.services.publication_request_service.cerrar_si_completa`). `True`
    requires every destino to be terminal (`PUBLICADO` or `CANCELADO`) and
    at least one to be `PUBLICADO` — a request with destinos but none
    successfully published is not "complete", it just has nothing left
    pending.
    """
    if not destinos:
        return False
    if not all(destino.es_terminal for destino in destinos):
        return False
    return any(destino.estado == EstadoDestino.PUBLICADO for destino in destinos)
