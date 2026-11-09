"""Domain service: an AI business advisor over a snapshot of the numbers.

The router condenses the business into a small dict of facts
(`foto_del_negocio`); this module only turns that into a prompt, makes ONE
structured AI call and validates the answer. The AI never touches the
database and cannot act: it returns suggestions for the owner to read.
It is told to ground every suggestion in the supplied numbers and to say
"no hay datos suficientes" instead of guessing — a figure the snapshot does
not contain must never appear in the answer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from core.ports.ai_provider import AIProvider, AIProviderError

PRIORIDADES = ("alta", "media", "baja")
AREAS = ("renovaciones", "cobranza", "finanzas", "operacion", "ventas", "redes")
_MAX_SUGERENCIAS = 8


class AsesorError(RuntimeError):
    """The advisor could not produce a usable answer."""


@dataclass(frozen=True, slots=True)
class Sugerencia:
    titulo: str
    detalle: str
    prioridad: str
    area: str
    cliente: str | None


@dataclass(frozen=True, slots=True)
class Analisis:
    resumen: str
    sugerencias: tuple[Sugerencia, ...]


_INSTRUCCIONES = """\
Eres el asesor de negocio de Portal Vallenato, un medio digital de vallenato \
que vende pautas (paquetes de publicaciones) a artistas, managers y empresas. \
Las pautas son principalmente para redes sociales; la web es un extra gratuito. \
El dueño trabaja solo con un equipo pequeño y quiere reducir su tiempo operativo, \
retener clientes, lograr renovaciones y mejorar sus números.

Reglas absolutas:
- Basa CADA sugerencia en los datos de abajo y cita la cifra o el cliente que la \
motiva. Nunca inventes cifras, clientes, fechas ni causas.
- Si los datos no alcanzan para concluir algo, dilo en lugar de suponer.
- Sugerencias concretas y accionables esta semana (qué hacer, con quién), no \
consejos genéricos. Prioriza lo que más dinero o clientes protege.
- Máximo 8 sugerencias, ordenadas de más a menos importante. Español natural, \
tono directo y respetuoso. No des asesoría legal ni tributaria.
- Los montos están en pesos colombianos (COP).
"""

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "resumen": {"type": "string", "minLength": 1, "maxLength": 800},
        "sugerencias": {
            "type": "array",
            "maxItems": _MAX_SUGERENCIAS,
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "minLength": 1, "maxLength": 120},
                    "detalle": {"type": "string", "minLength": 1, "maxLength": 700},
                    "prioridad": {"type": "string", "enum": list(PRIORIDADES)},
                    "area": {"type": "string", "enum": list(AREAS)},
                    "cliente": {"type": ["string", "null"]},
                },
                "required": ["titulo", "detalle", "prioridad", "area", "cliente"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["resumen", "sugerencias"],
    "additionalProperties": False,
}


def _extraer_json(respuesta: str | None) -> str:
    t = (respuesta or "").strip()
    i, f = t.find("{"), t.rfind("}")
    return t[i : f + 1] if 0 <= i < f else t


def analizar_negocio(foto: dict[str, Any], ai_provider: AIProvider) -> Analisis:
    """Return the advisor's reading of `foto`, or raise `AsesorError`."""
    prompt = (
        f"{_INSTRUCCIONES}\nDATOS DEL NEGOCIO (única fuente permitida):\n"
        f"{json.dumps(foto, ensure_ascii=False, default=str)}\n\n"
        'Devuelve ÚNICAMENTE un objeto JSON con "resumen" (2 a 4 frases sobre cómo '
        'va el negocio) y "sugerencias".'
    )
    try:
        respuesta = ai_provider.generate_structured(prompt, _SCHEMA)
    except AIProviderError as exc:
        raise AsesorError(f"La IA no está disponible: {exc}") from exc
    try:
        datos = json.loads(_extraer_json(respuesta))
        resumen = str(datos["resumen"]).strip()
        crudas = datos["sugerencias"]
        if not resumen or not isinstance(crudas, list):
            raise ValueError("forma inesperada")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AsesorError("La IA devolvió una respuesta inválida; inténtalo de nuevo.") from exc

    sugerencias: list[Sugerencia] = []
    for s in crudas[:_MAX_SUGERENCIAS]:
        if not isinstance(s, dict) or not s.get("titulo") or not s.get("detalle"):
            continue
        cliente = s.get("cliente")
        sugerencias.append(
            Sugerencia(
                titulo=str(s["titulo"]).strip(),
                detalle=str(s["detalle"]).strip(),
                prioridad=s.get("prioridad") if s.get("prioridad") in PRIORIDADES else "media",
                area=s.get("area") if s.get("area") in AREAS else "operacion",
                cliente=str(cliente) if isinstance(cliente, str) and cliente else None,
            )
        )
    return Analisis(resumen=resumen, sugerencias=tuple(sugerencias))
