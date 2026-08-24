"""Canned `AIProvider` — stands in for tests, no network, no API key.

Every generated value is prefixed `[DEMO]`, same discipline as
`agents.meta_social.fake_reader.FakeSocialMediaReader`: nothing here is a
real Claude response, and it must never be mistaken for one. Unlike that
reader, this fake takes optional constructor overrides — a caller can force
a specific JSON response or an `AIProviderError`, which
`tests/integration/api/test_publication_request_destinos_api.py` needs to
exercise both the AI-success and AI-failure paths of
`core.services.wordpress_publication_service.preparar_y_crear_borrador`.
`tests/integration/api/conftest.py` wires the zero-argument form (a
generic canned success) as the default for every test via
`app.dependency_overrides`.
"""

from __future__ import annotations

import json
from typing import Any

from core.ports.ai_provider import AIProviderError

_VALORES_DEMO: dict[str, Any] = {
    "titulo": "[DEMO] Titular generado por IA",
    "entradilla": "[DEMO] Entradilla generada por IA.",
    "contenido": "[DEMO] Contenido editorial generado por IA.",
    "categoria": None,
    "etiquetas": ["[DEMO] etiqueta"],
    "slug": "demo-titular-generado-por-ia",
}


def _respuesta_demo_desde_schema(json_schema: dict[str, Any]) -> dict[str, Any]:
    propiedades = json_schema.get("properties", {})
    return {nombre: _VALORES_DEMO.get(nombre, f"[DEMO] {nombre}") for nombre in propiedades}


class FakeAIProvider:
    """`AIProvider` backed by fixed, clearly-marked demo data (or a forced error)."""

    def __init__(
        self,
        *,
        respuesta_json: str | None = None,
        error: AIProviderError | None = None,
    ) -> None:
        self._respuesta_json = respuesta_json
        self._error = error

    def generate(self, prompt: str) -> str:
        if self._error is not None:
            raise self._error
        return self._respuesta_json or "[DEMO] respuesta de IA"

    def generate_structured(self, prompt: str, json_schema: dict[str, Any]) -> str:
        if self._error is not None:
            raise self._error
        if self._respuesta_json is not None:
            return self._respuesta_json
        return json.dumps(_respuesta_demo_desde_schema(json_schema))
