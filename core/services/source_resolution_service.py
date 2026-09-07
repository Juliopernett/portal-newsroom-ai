"""Domain service: resolve a NewsCandidate's source and extract its content.

Sprint Discovery 3 (2026-08-29) — the second half of "Discover" turning
into "usable materia prima": `descubrir` (Sprint Discovery 1) only knows
about the Google News redirect URL; this module resolves it to the real
article and extracts its content, one step at a time so each is
independently testable and reusable:

- `resolver_fuente` — `core.ports.source_resolver.SourceResolver` only.
- `preparar_contenido` — `core.ports.content_extractor.ContentExtractor`
  only, requires a resolved source first.
- `preparar_noticia` — composes both for the API layer's single
  "Preparar noticia" action.

Deliberately kept out of `core.services.news_candidate_service`, which
only holds pure editorial-review-state transitions — resolving/
extracting are I/O-bound pipeline steps with their own failure modes,
not a human decision like guardar/descartar/crear_noticia.

Every function here degrades gracefully instead of raising: same
discipline as `core.services.wordpress_publication_service
.preparar_y_crear_borrador` catching `EditorialAIError` — a failed
resolution or extraction must never break the Radar or lose the
candidate (docs/PROJECT_RULES.md rule 1's spirit: the system keeps going,
a human decides what to do next).
"""

from __future__ import annotations

from dataclasses import replace

from core.entities.news_candidate import EstadoResolucionFuente, NewsCandidate
from core.ports.content_extractor import ContentExtractor, ContentExtractorError
from core.ports.source_resolver import SourceResolver
from shared.logger import get_logger

logger = get_logger(__name__)


def resolver_fuente(candidato: NewsCandidate, resolver: SourceResolver) -> NewsCandidate:
    """Return a copy of `candidato` with `url` resolved to its real source.

    Always returns a candidate — never raises for a resolution failure.
    On failure, `estado_resolucion` becomes `FALLIDA` and
    `url_fuente_original` stays `None`; a future call can retry (this
    function is idempotent, not a one-shot).
    """
    resultado = resolver.resolve(candidato.url)
    if not resultado.success or resultado.resolved_url is None:
        logger.warning(
            "No se pudo resolver la fuente de '%s' (%s): %s",
            candidato.id,
            candidato.url,
            resultado.error,
        )
        return replace(candidato, estado_resolucion=EstadoResolucionFuente.FALLIDA)

    logger.info("Fuente resuelta para '%s': %s", candidato.id, resultado.resolved_url)
    return replace(
        candidato,
        url_fuente_original=resultado.resolved_url,
        estado_resolucion=EstadoResolucionFuente.RESUELTA,
    )


def preparar_contenido(candidato: NewsCandidate, extractor: ContentExtractor) -> NewsCandidate:
    """Return a copy of `candidato` with `extracted_content` populated.

    Requires `candidato.lista_para_extraccion` (i.e. `resolver_fuente`
    already succeeded) — raises `ValueError` otherwise, since extracting
    from an unresolved Google News redirect page would just capture
    Google's own interstitial, not the real article. Never raises for an
    extraction failure itself: `extracted_content` simply stays `None`,
    same graceful-degradation discipline as `resolver_fuente`.
    """
    if not candidato.lista_para_extraccion or candidato.url_fuente_original is None:
        raise ValueError(
            f"candidato '{candidato.id}' no tiene una fuente resuelta "
            f"(estado_resolucion={candidato.estado_resolucion.value!r}) — "
            "llama a resolver_fuente primero"
        )

    try:
        contenido = extractor.extract(candidato.url_fuente_original)
    except ContentExtractorError as exc:
        logger.warning(
            "No se pudo extraer contenido de '%s' para '%s': %s",
            candidato.url_fuente_original,
            candidato.id,
            exc,
        )
        return candidato

    logger.info(
        "Contenido extraído para '%s' desde '%s'", candidato.id, candidato.url_fuente_original
    )
    return replace(candidato, extracted_content=contenido)


def preparar_noticia(
    candidato: NewsCandidate, resolver: SourceResolver, extractor: ContentExtractor
) -> NewsCandidate:
    """Resolve `candidato`'s source and extract its content, in one call.

    The API's "Preparar noticia" action — composes `resolver_fuente` then
    `preparar_contenido`, skipping extraction if resolution failed. Never
    raises: a candidate that couldn't be resolved or extracted is
    returned as-is (marked `FALLIDA`, or resolved with no
    `extracted_content`), never dropped.
    """
    resuelto = resolver_fuente(candidato, resolver)
    if not resuelto.lista_para_extraccion:
        return resuelto
    return preparar_contenido(resuelto, extractor)
