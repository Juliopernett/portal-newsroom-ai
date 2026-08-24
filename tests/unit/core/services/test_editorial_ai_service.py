"""Unit tests for editorial_ai_service — no network, fake AIProvider."""

from __future__ import annotations

import json
from typing import Any

import pytest

from core.entities.publication_request import PublicationRequest
from core.ports.ai_provider import AIProviderError
from core.ports.cms_publisher import CategoriaCMS
from core.services.editorial_ai_service import (
    ContenidoEditorial,
    EditorialAIError,
    aplicar_preparacion_exitosa,
    aplicar_preparacion_fallida,
    generar_contenido_editorial,
)

_RESPUESTA_VALIDA = json.dumps(
    {
        "titulo": "Titular generado",
        "entradilla": "Entradilla generada.",
        "contenido": "Cuerpo reescrito.",
        "categoria": "Noticias",
        "etiquetas": ["vallenato", "lanzamiento"],
        "slug": "titular-generado",
    }
)


class _FakeAIProvider:
    """In-memory AIProvider — records the prompt/schema it received."""

    def __init__(self, respuesta: str | None = None, error: Exception | None = None) -> None:
        self._respuesta = respuesta
        self._error = error
        self.prompt_recibido: str | None = None
        self.schema_recibido: dict[str, Any] | None = None

    def generate(self, prompt: str) -> str:
        raise NotImplementedError("editorial_ai_service only uses generate_structured")

    def generate_structured(self, prompt: str, json_schema: dict[str, Any]) -> str:
        self.prompt_recibido = prompt
        self.schema_recibido = json_schema
        if self._error is not None:
            raise self._error
        assert self._respuesta is not None
        return self._respuesta


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {"texto": "Anuncio de nueva canción, sin firma"}
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def test_generar_contenido_editorial_returns_parsed_result() -> None:
    provider = _FakeAIProvider(respuesta=_RESPUESTA_VALIDA)
    categorias = [CategoriaCMS(id="3", nombre="Noticias")]

    resultado = generar_contenido_editorial(_solicitud(), categorias, provider)

    assert resultado == ContenidoEditorial(
        titulo="Titular generado",
        entradilla="Entradilla generada.",
        contenido="Cuerpo reescrito.",
        categoria="Noticias",
        etiquetas=("vallenato", "lanzamiento"),
        slug="titular-generado",
    )


def test_generar_contenido_editorial_includes_solicitud_texto_in_prompt() -> None:
    provider = _FakeAIProvider(respuesta=_RESPUESTA_VALIDA)
    solicitud = _solicitud(texto="Texto muy específico de esta solicitud")

    generar_contenido_editorial(solicitud, [], provider)

    assert provider.prompt_recibido is not None
    assert "Texto muy específico de esta solicitud" in provider.prompt_recibido


def test_generar_contenido_editorial_constrains_categoria_enum_to_existing_names() -> None:
    provider = _FakeAIProvider(respuesta=_RESPUESTA_VALIDA)
    categorias = [CategoriaCMS(id="1", nombre="Noticias"), CategoriaCMS(id="2", nombre="Crónicas")]

    generar_contenido_editorial(_solicitud(), categorias, provider)

    assert provider.schema_recibido is not None
    categoria_schema = provider.schema_recibido["properties"]["categoria"]
    enum_permitido = next(o["enum"] for o in categoria_schema["anyOf"] if "enum" in o)
    assert enum_permitido == ["Noticias", "Crónicas"]


def test_generar_contenido_editorial_raises_on_provider_failure() -> None:
    provider = _FakeAIProvider(error=AIProviderError("proveedor no configurado"))

    with pytest.raises(EditorialAIError, match="no configurado"):
        generar_contenido_editorial(_solicitud(), [], provider)


def test_generar_contenido_editorial_raises_on_malformed_json() -> None:
    provider = _FakeAIProvider(respuesta="esto no es json")

    with pytest.raises(EditorialAIError):
        generar_contenido_editorial(_solicitud(), [], provider)


def test_generar_contenido_editorial_raises_on_missing_required_key() -> None:
    provider = _FakeAIProvider(respuesta=json.dumps({"titulo": "Solo titulo"}))

    with pytest.raises(EditorialAIError):
        generar_contenido_editorial(_solicitud(), [], provider)


def test_aplicar_preparacion_exitosa_populates_editorial_fields() -> None:
    solicitud = _solicitud()
    contenido = ContenidoEditorial(
        titulo="T",
        entradilla="E",
        contenido="C",
        categoria="Noticias",
        etiquetas=("a", "b"),
        slug="t",
    )

    actualizada = aplicar_preparacion_exitosa(solicitud, contenido)

    assert actualizada.contenido_editorial == "C"
    assert actualizada.titulo_editorial == "T"
    assert actualizada.etiquetas_editorial == ("a", "b")
    assert actualizada.preparacion_ia_estado.value == "procesado"
    assert actualizada.preparacion_ia_error is None
    # original untouched
    assert solicitud.contenido_editorial is None


def test_aplicar_preparacion_fallida_keeps_texto_and_records_error() -> None:
    solicitud = _solicitud(texto="Texto original intacto")

    actualizada = aplicar_preparacion_fallida(solicitud, "la IA no respondió")

    assert actualizada.texto == "Texto original intacto"
    assert actualizada.preparacion_ia_estado.value == "fallido"
    assert actualizada.preparacion_ia_error == "la IA no respondió"
    assert actualizada.contenido_editorial is None


def test_aplicar_preparacion_fallida_truncates_a_very_long_error() -> None:
    solicitud = _solicitud()

    actualizada = aplicar_preparacion_fallida(solicitud, "x" * 5000)

    assert actualizada.preparacion_ia_error is not None
    assert len(actualizada.preparacion_ia_error) == 2000
