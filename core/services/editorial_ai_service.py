"""Domain service: turn a solicitud's raw texto into a WordPress-ready article.

Sprint 2026-08-21 — preparación editorial con IA. Depends only on
`core.ports.ai_provider.AIProvider` (a `Protocol`), never on a concrete SDK
— the real adapter (`agents.ai.anthropic_provider.AnthropicAIProvider`) is
wired in `app/api/dependencies.py`, so this module stays testable with a
fake, no network, per docs/PROJECT_RULES.md rule 5.

Exactly one AI call per solicitud (`generar_contenido_editorial`), using
`AIProvider.generate_structured` — the model's output is constrained to a
JSON Schema built fresh from the CMS's real categories, so it is
structurally incapable of inventing a category, and any other malformed
response raises `EditorialAIError` rather than silently corrupting a
`PublicationRequest`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

from core.entities.publication_request import EstadoPreparacionIA, PublicationRequest
from core.ports.ai_provider import AIProvider, AIProviderError
from core.ports.cms_publisher import CategoriaCMS

# Truncated before being stored in preparacion_ia_error — nothing else in
# the entity caps an internal-only diagnostic field, but an unbounded
# provider error message (a stack trace, a verbose API response) has no
# business growing a database row without limit.
_ERROR_MAX_CHARS = 2000

_SYSTEM_PROMPT = """\
Eres un editor periodístico de Portal Vallenato, un medio de noticias del \
género vallenato. Tu trabajo es tomar un texto recibido tal cual (a veces \
por WhatsApp, con errores de tipeo, sin estructura) y convertirlo en una \
noticia publicable, sin cambiar lo que dice.

Reglas absolutas, sin excepción:
- Nunca agregues fechas, cifras, lugares, nombres, declaraciones, citas \
ni ningún otro hecho que no esté explícitamente en el texto original. \
Ante la duda, conserva la redacción original literal en vez de asumir o \
completar información.
- No inventes contexto biográfico ni antecedentes que el texto no da.
- Corrige ortografía y puntuación, separa párrafos, elimina repeticiones \
evidentes, mejora la claridad y dale estructura periodística — pero el \
sentido y los hechos deben ser exactamente los del texto original.
- La categoría debe ser una de las categorías existentes que se te dan, \
o null si ninguna encaja bien — nunca inventes una categoría nueva.
- El slug debe ser corto, en minúsculas, con palabras separadas por \
guiones, sin tildes ni caracteres especiales.
"""


@dataclass(frozen=True, slots=True)
class ContenidoEditorial:
    """The AI's proposed rewrite of a solicitud, ready to hand to WordPress."""

    titulo: str
    entradilla: str
    contenido: str
    categoria: str | None
    etiquetas: tuple[str, ...]
    slug: str


class EditorialAIError(RuntimeError):
    """Raised when editorial AI preparation cannot produce a usable result.

    Covers every failure mode uniformly: `AIProviderError` (not
    configured, unreachable, refused) and a schema-conformant-but-invalid
    response (empty required field). Callers (see
    `core.services.wordpress_publication_service.preparar_y_crear_borrador`)
    catch this single type and fall back to the solicitud's raw texto —
    an AI outage must never block WordPress draft creation.
    """


def _construir_json_schema(categorias_existentes: list[str]) -> dict[str, Any]:
    """Return the JSON Schema constraining the model's structured output.

    `categoria`'s enum is built fresh from the CMS's real categories (plus
    `null`) — the model is structurally unable to propose a category that
    does not already exist in WordPress.
    """
    return {
        "type": "object",
        "properties": {
            "titulo": {"type": "string", "minLength": 1},
            "entradilla": {"type": "string", "minLength": 1},
            "contenido": {"type": "string", "minLength": 1},
            "categoria": {
                "anyOf": [
                    {"type": "string", "enum": categorias_existentes},
                    {"type": "null"},
                ]
            },
            "etiquetas": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "slug": {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"},
        },
        "required": ["titulo", "entradilla", "contenido", "categoria", "etiquetas", "slug"],
        "additionalProperties": False,
    }


def _construir_prompt(solicitud: PublicationRequest, categorias_existentes: list[str]) -> str:
    categorias_texto = (
        ", ".join(categorias_existentes) if categorias_existentes else "(ninguna disponible)"
    )
    titulo_operador = (
        f'\nTítulo sugerido por el operador (puede usarse, mejorarse, o '
        f'ignorarse si no encaja): "{solicitud.titulo}"'
        if solicitud.titulo
        else ""
    )
    return (
        "TEXTO ORIGINAL — única fuente de información permitida:\n"
        f"{solicitud.texto}\n"
        f"{titulo_operador}\n\n"
        f"Categorías existentes en WordPress (elige una de estas o deja "
        f"categoria en null si ninguna encaja): {categorias_texto}\n\n"
        "Devuelve la noticia lista para publicar como borrador."
    )


def generar_contenido_editorial(
    solicitud: PublicationRequest,
    categorias_existentes: list[CategoriaCMS],
    ai_provider: AIProvider,
) -> ContenidoEditorial:
    """Return the AI's editorial rewrite of `solicitud`, or raise `EditorialAIError`.

    Exactly one call to `ai_provider.generate_structured`. Never mutates
    `solicitud` — callers apply the result via `aplicar_preparacion_exitosa`.
    """
    nombres_categorias = [c.nombre for c in categorias_existentes]
    prompt = f"{_SYSTEM_PROMPT}\n\n{_construir_prompt(solicitud, nombres_categorias)}"
    schema = _construir_json_schema(nombres_categorias)
    try:
        respuesta = ai_provider.generate_structured(prompt, schema)
    except AIProviderError as exc:
        raise EditorialAIError(str(exc)) from exc
    try:
        datos = json.loads(respuesta)
    except (json.JSONDecodeError, TypeError) as exc:
        raise EditorialAIError(f"respuesta de IA no es JSON válido: {exc}") from exc
    try:
        return ContenidoEditorial(
            titulo=datos["titulo"],
            entradilla=datos["entradilla"],
            contenido=datos["contenido"],
            categoria=datos["categoria"],
            etiquetas=tuple(datos["etiquetas"]),
            slug=datos["slug"],
        )
    except (KeyError, TypeError) as exc:
        raise EditorialAIError(f"respuesta de IA no tiene la forma esperada: {exc}") from exc


def aplicar_preparacion_exitosa(
    solicitud: PublicationRequest, contenido: ContenidoEditorial
) -> PublicationRequest:
    """Return a copy of `solicitud` carrying `contenido`, marked PROCESADO."""
    return replace(
        solicitud,
        contenido_editorial=contenido.contenido,
        entradilla_editorial=contenido.entradilla,
        titulo_editorial=contenido.titulo,
        categoria_editorial=contenido.categoria,
        etiquetas_editorial=contenido.etiquetas,
        slug_editorial=contenido.slug,
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
        preparacion_ia_error=None,
    )


def aplicar_preparacion_fallida(solicitud: PublicationRequest, error: str) -> PublicationRequest:
    """Return a copy of `solicitud` marked FALLIDO, `texto` untouched.

    The caller still proceeds to create the WordPress draft from the raw
    `texto` — see `core.services.wordpress_publication_service
    .preparar_y_crear_borrador`. This function only records that the
    automatic step did not run this time.
    """
    return replace(
        solicitud,
        preparacion_ia_estado=EstadoPreparacionIA.FALLIDO,
        preparacion_ia_error=error[:_ERROR_MAX_CHARS],
    )
