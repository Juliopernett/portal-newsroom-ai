"""Domain service: per-network post text (Instagram / Facebook), on demand.

Optional and human-approved: the operator presses a button per destino; the
client's own text is never touched unless they choose to use the result.
Hard limits are enforced in code, not only in the prompt — a model that
ignores "max 5 hashtags" still cannot return more (`limitar_hashtags`), and
in `AJUSTAR` mode a response that drops a @mention, link or number from the
client's text is rejected (`TextoRedesError`) rather than shown.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Any

from core.entities.destino_publicacion import CanalPublicacion
from core.ports.ai_provider import AIProvider, AIProviderError

MAX_HASHTAGS: dict[CanalPublicacion, int] = {
    CanalPublicacion.INSTAGRAM: 5,
    CanalPublicacion.FACEBOOK: 2,
}

_HASHTAG = re.compile(r"(?<!\w)#\w+", re.UNICODE)
_PROTEGIDOS = re.compile(r"https?://\S+|@\w+|\d[\d\s.\-]{5,}\d", re.UNICODE)


class ModoTexto(StrEnum):
    AJUSTAR = "ajustar"  # respeta el mensaje del cliente: formato + hashtags
    REDACTAR = "redactar"  # solo hay una idea: propone un borrador


class TextoRedesError(RuntimeError):
    """The AI could not produce a usable text for this destino."""


def limitar_hashtags(texto: str, maximo: int) -> str:
    """Keep only the first `maximo` distinct hashtags; drop the rest from the text."""
    vistos: list[str] = []

    def _reemplazo(m: re.Match[str]) -> str:
        etiqueta = m.group(0)
        clave = etiqueta.lower()
        if clave in vistos:
            return ""
        if len(vistos) >= maximo:
            return ""
        vistos.append(clave)
        return etiqueta

    limpio = _HASHTAG.sub(_reemplazo, texto)
    limpio = re.sub(r"[ \t]+\n", "\n", limpio)
    return re.sub(r"\n{3,}", "\n\n", limpio).strip()


def contar_hashtags(texto: str) -> int:
    return len({m.group(0).lower() for m in _HASHTAG.finditer(texto)})


def _normalizar(valor: str) -> str:
    return re.sub(r"[\s.\-]", "", valor).lower().rstrip(".,;:)")


def datos_perdidos(original: str, generado: str) -> list[str]:
    """Return @mentions/links/numbers of `original` that `generado` lost."""
    destino = _normalizar(generado)
    return [
        m.group(0).strip()
        for m in _PROTEGIDOS.finditer(original)
        if _normalizar(m.group(0)) not in destino
    ]


_GUIA_CANAL = {
    CanalPublicacion.INSTAGRAM: (
        "Instagram: texto breve y directo, primera línea con gancho, máximo 3 emojis, "
        "y AL FINAL como máximo 5 hashtags (nunca más de 5)."
    ),
    CanalPublicacion.FACEBOOK: (
        "Facebook: texto algo más desarrollado y conversacional, como mucho 2 hashtags."
    ),
}

_MODO_TEXTO = {
    ModoTexto.AJUSTAR: (
        "El cliente ya trae su texto. RESPÉTALO: conserva su mensaje, tono y cada dato "
        "(nombres, @menciones, enlaces, teléfonos, fechas, cifras) exactamente igual. "
        "Solo corrige ortografía, ordena el formato para la red y agrega los hashtags."
    ),
    ModoTexto.REDACTAR: (
        "Solo llegó una idea o notas sueltas. Redacta un borrador atractivo usando "
        "ÚNICAMENTE lo que dice el texto; si falta un dato (fecha, lugar), no lo "
        "inventes ni lo menciones."
    ),
}


def _prompt(texto: str, titulo: str | None, canal: CanalPublicacion, modo: ModoTexto) -> str:
    cabecera = (
        "Eres community manager de Portal Vallenato, medio de noticias del género "
        "vallenato. Prepara el texto de una publicación para una red social.\n"
        "Reglas absolutas: nunca inventes hechos, fechas, cifras, lugares ni declaraciones; "
        "no uses clickbait engañoso; escribe en español natural.\n"
    )
    t = f'\nTítulo de referencia: "{titulo}"' if titulo else ""
    return (
        f"{cabecera}{_MODO_TEXTO[modo]}\n{_GUIA_CANAL[canal]}\n\n"
        f"TEXTO ORIGINAL — única fuente permitida:\n{texto}{t}\n\n"
        'Devuelve ÚNICAMENTE un objeto JSON con la clave "texto".'
    )


_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"texto": {"type": "string", "minLength": 1, "maxLength": 2000}},
    "required": ["texto"],
    "additionalProperties": False,
}


def _extraer_json(respuesta: str | None) -> str:
    t = (respuesta or "").strip()
    i, f = t.find("{"), t.rfind("}")
    return t[i : f + 1] if 0 <= i < f else t


def generar_texto_red(
    texto: str,
    titulo: str | None,
    canal: CanalPublicacion,
    modo: ModoTexto,
    ai_provider: AIProvider,
) -> str:
    """Return the AI's text for `canal`, hashtags capped. Raises `TextoRedesError`."""
    if canal not in MAX_HASHTAGS:
        raise TextoRedesError("El texto por red solo aplica a Facebook e Instagram.")
    if not texto.strip():
        raise TextoRedesError("La solicitud no tiene texto de partida.")
    try:
        respuesta = ai_provider.generate_structured(_prompt(texto, titulo, canal, modo), _SCHEMA)
    except AIProviderError as exc:
        raise TextoRedesError(f"La IA no está disponible: {exc}") from exc
    try:
        generado = str(json.loads(_extraer_json(respuesta))["texto"]).strip()
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise TextoRedesError("La IA devolvió una respuesta inválida; inténtalo de nuevo.") from exc
    if not generado:
        raise TextoRedesError("La IA devolvió un texto vacío; inténtalo de nuevo.")
    generado = limitar_hashtags(generado, MAX_HASHTAGS[canal])
    if modo is ModoTexto.AJUSTAR:
        perdidos = datos_perdidos(texto, generado)
        if perdidos:
            raise TextoRedesError(
                "La IA alteró datos del cliente (" + ", ".join(perdidos[:3]) + "). "
                "Usa el texto original o pasa a «Redactar desde la idea»."
            )
    return generado
