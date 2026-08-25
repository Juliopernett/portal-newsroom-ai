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

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.ports.cms_publisher import CMSPublisher, EstadoPostCMS
from shared.logger import get_logger

logger = get_logger(__name__)


def marcar_publicado(
    destino: DestinoPublicacion,
    *,
    registrado_por_user_id: str | None = None,
    fecha_publicacion: datetime | None = None,
    wp_post_id: str | None = None,
    wp_url: str | None = None,
    url_publicacion: str | None = None,
    meta_post_id: str | None = None,
) -> DestinoPublicacion:
    """Return a copy of `destino` transitioned to `PUBLICADO`.

    Allowed from `PENDIENTE` or `FALLIDO` (a retried failure can still
    succeed) — raises `ValueError` if `destino` is already terminal
    (`PUBLICADO`/`CANCELADO`). `fecha_publicacion` defaults to now (UTC)
    when not given, same convention as `Pauta.fecha_registro`'s own
    `default_factory`. `meta_post_id` is only ever set when the operator
    "relacionó" a real Meta post via the posts-recientes picker — a plain
    manually-typed `url_publicacion` (Facebook/Instagram) or a WordPress
    destino leaves it `None`, same as before this field existed.
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
        meta_post_id=meta_post_id if meta_post_id is not None else destino.meta_post_id,
    )


def corregir_enlace(
    destino: DestinoPublicacion,
    *,
    wp_url: str | None = None,
    url_publicacion: str | None = None,
    meta_post_id: str | None = None,
) -> DestinoPublicacion:
    """Return a copy of `destino` with its link corrected — a data-entry fix,
    not a state transition (see `marcar_publicado` for the real one).

    Added after a real incident: an operator pasted the wrong Instagram
    link while confirming several destinos back-to-back, and there was no
    way to fix it short of editing the database directly. Only allowed
    once already `PUBLICADO` — a destino that hasn't been confirmed yet
    has nothing to correct, that's what `marcar_publicado` is for. Never
    touches `estado` or `fecha_publicacion`: correcting *what* was
    published is not the same as re-publishing it, so quota/`fecha_cierre`
    never get recomputed by this. `__post_init__` still enforces that
    `wp_url` only applies to WORDPRESS and `url_publicacion`/`meta_post_id`
    only to FACEBOOK/INSTAGRAM. `meta_post_id` re-picking a post from the
    picker keeps the dedup record in sync with the corrected link — a
    plain manual retype leaves it as it was (never cleared implicitly).
    """
    if destino.estado != EstadoDestino.PUBLICADO:
        raise ValueError(
            f"cannot correct the link of a destino that is not PUBLICADO "
            f"(estado={destino.estado.value!r})"
        )
    return replace(
        destino,
        wp_url=wp_url if wp_url is not None else destino.wp_url,
        url_publicacion=url_publicacion if url_publicacion is not None else destino.url_publicacion,
        meta_post_id=meta_post_id if meta_post_id is not None else destino.meta_post_id,
    )


def sincronizar_estado_wordpress(
    destino: DestinoPublicacion, cms_publisher: CMSPublisher
) -> DestinoPublicacion:
    """Return `destino` reconciled against WordPress's real, current state.

    Sprint 2026-08-24 — lets the operator publish directly in WordPress
    without a separate manual "Confirmar publicado" step in Newsroom being
    the only way this system ever finds out. A no-op (no call to
    `cms_publisher` at all) when there is nothing to sync: not a
    WordPress destino, no `wp_post_id` yet (draft never created), or
    already terminal (`PUBLICADO`/`CANCELADO` — nothing left to detect).

    `CMSPublisher.consultar_estado_post` never raises, so every branch
    here is a plain state mapping, never a try/except:
    - `PUBLICADO` in WordPress → `marcar_publicado`, with the real url/
      fecha WordPress reports.
    - `ELIMINADO` (moved to trash) → `marcar_fallido`, reusing the
      existing FALLIDO estado with a descriptive message instead of
      adding a new EstadoDestino — FALLIDO is already retriable/
      cancellable, so the operator can decide what to do next.
    - `ERROR` (network/credentials/unexpected response) → only
      `ultimo_error` is updated; `estado`/`wp_url`/`fecha_publicacion` are
      left untouched — a failed verification attempt must never destroy
      what was already known.
    - `BORRADOR` → unchanged, still waiting.
    """
    if destino.canal is not CanalPublicacion.WORDPRESS or destino.wp_post_id is None:
        return destino
    if destino.es_terminal:
        return destino
    consulta = cms_publisher.consultar_estado_post(destino.wp_post_id)
    if consulta.estado is EstadoPostCMS.PUBLICADO:
        actualizado = marcar_publicado(
            destino,
            fecha_publicacion=consulta.fecha_publicacion,
            wp_url=consulta.url or destino.wp_url,
        )
        logger.info("Destino %s sincronizado: WordPress lo reporta publicado.", destino.id)
        return actualizado
    if consulta.estado is EstadoPostCMS.ELIMINADO:
        actualizado = marcar_fallido(
            destino, error="El borrador fue movido a la papelera en WordPress."
        )
        logger.info("Destino %s sincronizado: WordPress lo reporta en la papelera.", destino.id)
        return actualizado
    if consulta.estado is EstadoPostCMS.ERROR:
        return replace(
            destino, ultimo_error="No se pudo verificar el estado en WordPress ahora mismo."
        )
    return destino


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


def puede_eliminarse_sin_afectar_completitud(
    destino: DestinoPublicacion, otros_destinos: Sequence[DestinoPublicacion]
) -> bool:
    """Return whether removing `destino` (not in `otros_destinos`) leaves
    `esta_completa` unchanged for the rest of the solicitud's destinos.

    There is no domain-level "eliminar" transition — deleting a row is a
    persistence concern (`DestinoPublicacionRepository.delete`), not a
    state one. This is the one check every caller of that delete must run
    first: it exists for cases like a WordPress destino `publish()`
    stamped automatically (see `app.api.routers.publication_requests.
    publish_publication_request`) that turned out redundant once a real
    Facebook/Instagram destino was registered for the same solicitud —
    removing it must never flip `esta_completa` from `True` to `False`
    (would silently reopen a solicitud, clear `fecha_cierre`, and
    un-consume its pauta's cupo) nor, for symmetry, from `False` to `True`.
    """
    return esta_completa([destino, *otros_destinos]) == esta_completa(otros_destinos)


def tiene_destino_social(destinos: Sequence[DestinoPublicacion]) -> bool:
    """Return whether any of `destinos` is a Facebook or Instagram one, in any estado.

    Backs the "Sin destino (contratos activos)" filter in Solicitudes —
    a solicitud published only through the WordPress placeholder (see
    `app.api.routers.publication_requests.publish_publication_request`)
    has no real social-media link yet, regardless of that WordPress
    destino's own estado.
    """
    return any(
        destino.canal in (CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM)
        for destino in destinos
    )


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
