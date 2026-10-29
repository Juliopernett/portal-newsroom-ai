"""Domain service: turn a NewsCandidate into a WordPress draft.

Sprint Discovery 5 (2026-10-29). "Crear noticia" in the Radar Editorial:
rewrites the candidate's `extracted_content` with the editorial AI (same
prompt, schema and Yoast fields as `core.services.editorial_ai_service`,
plus the rules for rewriting another outlet's note) and creates a
**draft** in WordPress — never a published post (docs/PROJECT_RULES.md
rule 1). A human still reviews and publishes it in WordPress.

Deliberately stricter than `core.services.wordpress_publication_service
.preparar_y_crear_borrador`: there, an AI failure falls back to the raw
`texto` the client sent us. Here the raw text is *another outlet's
article*, so falling back would republish it verbatim — instead an AI
failure aborts with `BorradorDesdeCandidatoError` and nothing is created.

The extracted image is never used: it belongs to the original outlet. A
featured image is attached only when the operator supplies their own
photo (`PortadaParaBorrador`) — it is rendered into the branded cover
(Sprint Portadas), uploaded to WordPress, and its URL is kept on the
candidate so the same image can go to social networks.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from html import escape
from typing import Any

from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate
from core.ports.ai_provider import AIProvider
from core.ports.cms_publisher import CMSPublisher
from core.ports.portada_renderer import PortadaRenderer, SolicitudPortada, VariantePortada
from core.services.editorial_ai_service import (
    REGLAS_NOTA_DE_OTRO_MEDIO,
    ContenidoEditorial,
    EditorialAIError,
    generar_contenido_editorial_desde_texto,
)
from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class PortadaParaBorrador:
    """The operator's choices for the cover that becomes the draft's featured image.

    `titular=None` means "use the headline the AI writes for the article".
    """

    imagen_base: bytes
    variante: VariantePortada = VariantePortada.NOTICIAS
    titular: str | None = None
    antetitulo: str | None = None
    imagen_circulo: bytes | None = None
    enfoque_x: float = 0.5
    enfoque_y: float = 0.3


class BorradorDesdeCandidatoError(RuntimeError):
    """The editorial AI could not produce a usable rewrite — no draft was created."""


def _pie_de_fuente(candidato: NewsCandidate) -> str:
    contenido = candidato.extracted_content
    assert contenido is not None
    nombre = contenido.site_name or candidato.source
    enlace = escape(contenido.source_url)
    return f'<p>Fuente: <a href="{enlace}" rel="nofollow noopener">{escape(nombre)}</a></p>'


def construir_contenido_borrador(
    candidato: NewsCandidate, contenido: ContenidoEditorial
) -> dict[str, Any]:
    """Return the `{title, content, ...}` payload for `CMSPublisher.create_draft`."""
    payload: dict[str, Any] = {
        "title": contenido.titulo,
        "content": f"{contenido.contenido}\n\n{_pie_de_fuente(candidato)}",
    }
    if contenido.entradilla:
        payload["excerpt"] = contenido.entradilla
    if contenido.slug:
        payload["slug"] = contenido.slug
    meta: dict[str, str] = {}
    if contenido.meta_titulo:
        meta["_yoast_wpseo_title"] = contenido.meta_titulo
    if contenido.meta_descripcion:
        meta["_yoast_wpseo_metadesc"] = contenido.meta_descripcion
    if contenido.frase_clave:
        meta["_yoast_wpseo_focuskw"] = contenido.frase_clave
    if meta:
        payload["meta"] = meta
    return payload


def crear_borrador_desde_candidato(
    candidato: NewsCandidate,
    ai_provider: AIProvider,
    cms_publisher: CMSPublisher,
    *,
    portada: PortadaParaBorrador | None = None,
    portada_renderer: PortadaRenderer | None = None,
) -> NewsCandidate:
    """Rewrite `candidato` with the editorial AI and create its WordPress draft.

    Returns a copy marked `PROCESADO` carrying `wp_post_id`/`wp_url`. If
    `cms_publisher` fails, the exception propagates uncaught so the
    caller's `UnitOfWork` rolls back and the action is safely retriable.

    With `portada` (and a `portada_renderer`), the cover is rendered after
    the AI writes the headline, uploaded to WordPress as the draft's
    featured image, and its URL stored in `portada_url`. A cover that
    cannot be rendered (`PortadaError`, a `ValueError`) aborts before
    anything is created in WordPress.

    Raises `ValueError` if `candidato` is already terminal, or has no
    `extracted_content` yet (run "Preparar noticia" first), and
    `BorradorDesdeCandidatoError` if the AI step fails.
    """
    if portada is not None and portada_renderer is None:
        raise ValueError("portada_renderer is required when a portada is requested")
    if candidato.es_terminal:
        raise ValueError(
            f"cannot create a draft for a candidato already in a terminal estado "
            f"({candidato.estado.value!r})"
        )
    extraido = candidato.extracted_content
    if extraido is None:
        raise ValueError(
            "El candidato aún no tiene contenido extraído — usa «Preparar noticia» primero"
        )

    categorias = cms_publisher.listar_categorias()
    try:
        contenido = generar_contenido_editorial_desde_texto(
            extraido.body,
            extraido.title,
            categorias,
            ai_provider,
            reglas_adicionales=REGLAS_NOTA_DE_OTRO_MEDIO,
        )
    except EditorialAIError as exc:
        logger.warning("Redacción con IA falló para candidato %s: %s", candidato.id, exc)
        raise BorradorDesdeCandidatoError(str(exc)) from exc

    payload = construir_contenido_borrador(candidato, contenido)
    if contenido.categoria:
        coincidencia = next(
            (c for c in categorias if c.nombre.lower() == contenido.categoria.lower()), None
        )
        if coincidencia is not None:
            payload["categories"] = [coincidencia.id]
    etiquetas = [e for e in contenido.etiquetas if e and e.strip()]
    if etiquetas:
        payload["tags"] = [cms_publisher.resolver_o_crear_etiqueta(e) for e in etiquetas]

    portada_url: str | None = None
    if portada is not None and portada_renderer is not None:
        imagen = portada_renderer.renderizar(
            SolicitudPortada(
                imagen_base=portada.imagen_base,
                titular=portada.titular or contenido.titulo,
                variante=portada.variante,
                antetitulo=portada.antetitulo,
                imagen_circulo=portada.imagen_circulo,
                enfoque_x=portada.enfoque_x,
                enfoque_y=portada.enfoque_y,
            ),
            formato="jpeg",
        )
        subida = cms_publisher.subir_media_con_url(
            imagen, f"portada-{contenido.slug}.jpg", "image/jpeg"
        )
        payload["featured_media"] = subida.id
        portada_url = subida.url

    resultado = cms_publisher.create_draft(payload)
    logger.info(
        "Borrador %s creado en WordPress para candidato %s", resultado.post_id, candidato.id
    )
    return replace(
        candidato,
        estado=EstadoNewsCandidate.PROCESADO,
        wp_post_id=resultado.post_id,
        wp_url=resultado.url,
        portada_url=portada_url,
    )
