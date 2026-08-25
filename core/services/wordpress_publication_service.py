"""Domain service: build WordPress draft content and attach the result to
a DestinoPublicacion.

Sprint 4A, Increment 3 (see docs/adr/ADR-006-multichannel-publication.md,
Decision 4). Depends only on `core.ports.cms_publisher.CMSPublisher`
(a `Protocol`), never on `agents.wordpress.client` directly — the real
adapter is wired in `app/api/dependencies.py`, so this module stays
testable with a fake publisher, no network, per docs/PROJECT_RULES.md
rule 5.

`preparar_y_crear_borrador` (Sprint 2026-08-21, preparación editorial con
IA) is the new entry point the API router calls: it runs the AI rewrite
(falling back to raw `texto` if the AI is unavailable or fails), resolves
a matching WordPress category and tags, attaches a featured image if the
solicitud has one, and then creates the draft — all in one pass, still a
single WordPress draft, still never published automatically.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion
from core.entities.media_asset import MediaAsset, MediaAssetType
from core.entities.publication_request import EstadoPreparacionIA, PublicationRequest
from core.ports.ai_provider import AIProvider
from core.ports.cms_publisher import CMSPublisher
from core.ports.media_storage import MediaStorage
from core.services.editorial_ai_service import (
    EditorialAIError,
    aplicar_preparacion_exitosa,
    aplicar_preparacion_fallida,
    generar_contenido_editorial,
)
from shared.logger import get_logger

logger = get_logger(__name__)


def construir_contenido_wordpress(solicitud: PublicationRequest) -> dict[str, Any]:
    """Return the `{title, content, ...}` payload a CMSPublisher.create_draft needs.

    Prefers the AI-prepared editorial fields when `preparacion_ia_estado`
    is `PROCESADO`; falls back to the operator-entered `titulo`/raw `texto`
    otherwise — either because the AI step never ran, or it failed (see
    `preparar_y_crear_borrador`). `texto` itself is never read for the
    title fallback's 60-char slice unless there is truly no better title,
    same behavior as before this field existed. Typed `dict[str, Any]`,
    not `dict[str, str]`, so `preparar_y_crear_borrador` can still add
    `categories`/`tags` (lists) afterward.
    """
    if solicitud.preparacion_ia_estado == EstadoPreparacionIA.PROCESADO:
        content: dict[str, Any] = {
            "title": solicitud.titulo or solicitud.titulo_editorial or solicitud.texto[:60],
            "content": solicitud.contenido_editorial or solicitud.texto,
        }
        if solicitud.entradilla_editorial:
            content["excerpt"] = solicitud.entradilla_editorial
        if solicitud.slug_editorial:
            content["slug"] = solicitud.slug_editorial
        # Yoast SEO's own fields (confirmed REST-settable on the live
        # WordPress site — show_in_rest=true on all three, checked via
        # `wp eval`, 2026-08-25) — feeds the exact same score Yoast shows
        # for every manually-published post, instead of leaving every
        # AI-prepared draft flagged "necesita mejorar".
        meta: dict[str, str] = {}
        if solicitud.meta_titulo_editorial:
            meta["_yoast_wpseo_title"] = solicitud.meta_titulo_editorial
        if solicitud.meta_descripcion_editorial:
            meta["_yoast_wpseo_metadesc"] = solicitud.meta_descripcion_editorial
        if solicitud.frase_clave_editorial:
            meta["_yoast_wpseo_focuskw"] = solicitud.frase_clave_editorial
        if meta:
            content["meta"] = meta
        return content
    return {
        "title": solicitud.titulo or solicitud.texto[:60],
        "content": solicitud.texto,
    }


def _validar_destino_wordpress(destino: DestinoPublicacion) -> None:
    if destino.canal != CanalPublicacion.WORDPRESS:
        raise ValueError(
            f"crear_borrador only applies to canal={CanalPublicacion.WORDPRESS.value!r}, "
            f"got canal={destino.canal.value!r}"
        )
    if destino.es_terminal:
        raise ValueError(
            f"cannot create a WordPress draft for a destino already in a terminal estado "
            f"({destino.estado.value!r})"
        )


def crear_borrador(
    destino: DestinoPublicacion,
    content: dict[str, Any],
    cms_publisher: CMSPublisher,
) -> DestinoPublicacion:
    """Return a copy of `destino` with `wp_post_id`/`wp_url` from a new WordPress draft.

    Does not change `destino.estado` — creating a draft is not the same
    as being published (docs/PROJECT_RULES.md rule 1); `destino` stays
    `PENDIENTE`, carrying the draft's identifiers, until a human confirms
    the post actually went live (a separate step,
    `core.services.destino_publicacion_service.marcar_publicado`).

    `content` is the already-built payload (see
    `construir_contenido_wordpress` and `preparar_y_crear_borrador`) — this
    function no longer builds it from a `PublicationRequest` itself, so a
    caller can enrich it (category, tags, featured image) before the draft
    is created.

    Raises `ValueError` if `destino.canal` is not `WORDPRESS`, or if
    `destino` is already terminal (`PUBLICADO`/`CANCELADO` — no draft
    needs creating for either).
    """
    _validar_destino_wordpress(destino)
    resultado = cms_publisher.create_draft(content)
    return replace(destino, wp_post_id=resultado.post_id, wp_url=resultado.url)


def _primera_imagen(media_assets: Sequence[MediaAsset]) -> MediaAsset | None:
    """Return the earliest-uploaded IMAGEN MediaAsset, or None.

    The featured-image convention (Sprint 2026-08-21): no new column, no
    "marcar como destacada" UI — the first image attached is the
    candidate, exactly the increment docs/adr/ADR-007-media-assets.md
    already anticipated ("buen candidato a incremento futuro").
    """
    imagenes = sorted(
        (m for m in media_assets if m.tipo == MediaAssetType.IMAGEN),
        key=lambda m: m.fecha_subida,
    )
    return imagenes[0] if imagenes else None


def preparar_y_crear_borrador(
    destino: DestinoPublicacion,
    solicitud: PublicationRequest,
    media_assets: Sequence[MediaAsset],
    ai_provider: AIProvider,
    cms_publisher: CMSPublisher,
    media_storage: MediaStorage,
) -> tuple[DestinoPublicacion, PublicationRequest]:
    """Prepare `solicitud`'s content with AI, then create its WordPress draft.

    Single transaction, all-or-nothing, matching the shape
    `crear_borrador` already had: if `cms_publisher` itself fails at any
    step (listing categories, resolving tags, uploading the image, or
    creating the draft), the exception propagates uncaught — the caller's
    `UnitOfWork` rolls back everything, `solicitud` is left exactly as it
    was, and clicking "Crear borrador" again retries cleanly (re-running
    the AI step too, an accepted small cost — see
    docs/adr/ADR-007-media-assets.md's own "ship simple, revisit if it's a
    real problem" precedent).

    If the AI step itself fails (not configured, unreachable, refused, or
    a malformed response — anything `core.services.editorial_ai_service`
    raises as `EditorialAIError`), it is caught here: `solicitud` is
    stamped `FALLIDO` with the error, and the draft is still created from
    the raw `texto` — an AI outage must never block the WordPress
    integration (docs/PROJECT_RULES.md's spirit of graceful degradation).

    Returns the updated `(destino, solicitud)` — the caller (the API
    router) persists both in the same commit.
    """
    _validar_destino_wordpress(destino)
    categorias = cms_publisher.listar_categorias()

    if solicitud.preparacion_ia_estado != EstadoPreparacionIA.PROCESADO:
        try:
            contenido = generar_contenido_editorial(solicitud, categorias, ai_provider)
            solicitud = aplicar_preparacion_exitosa(solicitud, contenido)
            logger.info("Preparación editorial IA exitosa para solicitud %s", solicitud.id)
        except EditorialAIError as exc:
            logger.warning(
                "Preparación editorial IA falló para solicitud %s: %s", solicitud.id, exc
            )
            solicitud = aplicar_preparacion_fallida(solicitud, str(exc))

    content = construir_contenido_wordpress(solicitud)

    if solicitud.preparacion_ia_estado == EstadoPreparacionIA.PROCESADO:
        if solicitud.categoria_editorial:
            coincidencia = next(
                (
                    c
                    for c in categorias
                    if c.nombre.lower() == solicitud.categoria_editorial.lower()
                ),
                None,
            )
            if coincidencia is not None:
                content["categories"] = [coincidencia.id]
        if solicitud.etiquetas_editorial:
            content["tags"] = [
                cms_publisher.resolver_o_crear_etiqueta(nombre)
                for nombre in solicitud.etiquetas_editorial
            ]

    imagen = _primera_imagen(media_assets)
    if imagen is not None:
        try:
            contenido_bytes = media_storage.leer(imagen.storage_key)
        except FileNotFoundError:
            # The DB row survived but the underlying file did not (same
            # documented failure mode as `descargar_media` in
            # app.api.routers.publication_requests) — not a reason to
            # block an otherwise-clean draft.
            logger.warning(
                "MediaAsset %s de solicitud %s no tiene contenido en storage; "
                "borrador se crea sin imagen destacada",
                imagen.id,
                solicitud.id,
            )
        else:
            media_id = cms_publisher.subir_media(
                contenido_bytes, imagen.nombre_archivo, imagen.content_type
            )
            content["featured_media"] = media_id

    destino_creado = crear_borrador(destino, content, cms_publisher)
    return destino_creado, solicitud
