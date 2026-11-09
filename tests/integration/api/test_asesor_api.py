"""Integration tests: POST /insights/asesor (AI business advisor)."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agents.ai.fake_provider import FakeAIProvider
from app.api.dependencies import get_ai_provider
from app.api.main import app
from core.ports.ai_provider import AIProviderError


@pytest.fixture(autouse=True)
def _restaurar_ia() -> Iterator[None]:
    yield
    app.dependency_overrides.pop(get_ai_provider, None)


def test_asesor_returns_validated_suggestions(client: TestClient) -> None:
    respuesta = {
        "resumen": "Va bien.",
        "sugerencias": [
            {"titulo": "A", "detalle": "d", "prioridad": "rara", "area": "x", "cliente": None},
            {"titulo": "", "detalle": "v", "prioridad": "alta", "area": "ventas", "cliente": None},
        ],
    }
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(
        respuesta_json=json.dumps(respuesta)
    )

    r = client.post("/insights/asesor")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["resumen"] == "Va bien."
    assert len(body["sugerencias"]) == 1  # the empty-title one is dropped
    assert body["sugerencias"][0]["prioridad"] == "media"  # unknown value normalized
    assert body["sugerencias"][0]["area"] == "operacion"


def test_asesor_ai_outage_is_a_clear_422(client: TestClient) -> None:
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(
        error=AIProviderError("sin clave")
    )

    r = client.post("/insights/asesor")

    assert r.status_code == 422
    assert "IA no está disponible" in r.json()["detail"]


def test_asesor_requires_login(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.post("/insights/asesor").status_code == 401
