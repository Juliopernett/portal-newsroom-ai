"""Integration tests: optional per-network text (Instagram/Facebook) with AI."""

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


def _ia(texto: str | None = None, error: AIProviderError | None = None) -> None:
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(
        respuesta_json=json.dumps({"texto": texto}) if texto is not None else None, error=error
    )


def _destino(client: TestClient, canal: str, texto: str = "Silvestre toca en Valledupar") -> tuple:
    cid = client.post(
        "/clients", json={"nombre": "Cliente", "tipo": "artista", "telefono": "300"}
    ).json()["id"]
    pid = client.post(
        "/pautas",
        json={
            "client_id": cid,
            "fecha_inicio": "2026-07-30",
            "fecha_fin": "2026-08-30",
            "publicaciones_contratadas": 10,
            "valor_pagado": "500000.00",
            "fecha_pago": "2026-07-30",
        },
    ).json()["id"]
    sid = client.post("/publication-requests", json={"pauta_id": pid, "texto": texto}).json()["id"]
    did = client.post(f"/publication-requests/{sid}/destinos", json={"canal": canal}).json()["id"]
    return sid, did


def test_instagram_text_is_capped_at_five_hashtags_by_code(client: TestClient) -> None:
    _ia("Gran noticia #a #b #c #d #e #f #g")
    sid, did = _destino(client, "instagram")

    r = client.post(f"/publication-requests/{sid}/destinos/{did}/texto-ia", json={"modo": "redactar"})

    assert r.status_code == 200, r.text
    assert r.json()["texto_ia"] == "Gran noticia #a #b #c #d #e"


def test_ajustar_rejects_a_text_that_drops_client_data(client: TestClient) -> None:
    _ia("Concierto en Valledupar")
    sid, did = _destino(client, "instagram", "Concierto con @silvestre llama 3001234567")

    r = client.post(f"/publication-requests/{sid}/destinos/{did}/texto-ia", json={"modo": "ajustar"})

    assert r.status_code == 422
    assert "@silvestre" in r.json()["detail"]


def test_ajustar_accepts_a_text_that_keeps_client_data(client: TestClient) -> None:
    _ia("Concierto con @silvestre. Info: 300 123 4567 #vallenato")
    sid, did = _destino(client, "instagram", "Concierto con @silvestre llama 3001234567")

    r = client.post(f"/publication-requests/{sid}/destinos/{did}/texto-ia", json={"modo": "ajustar"})

    assert r.status_code == 200, r.text


def test_ai_outage_is_a_clear_422_and_saves_nothing(client: TestClient) -> None:
    _ia(error=AIProviderError("sin clave"))
    sid, did = _destino(client, "facebook")

    r = client.post(f"/publication-requests/{sid}/destinos/{did}/texto-ia", json={})

    assert r.status_code == 422
    destinos = client.get(f"/publication-requests/{sid}/destinos").json()
    assert destinos[0]["texto_ia"] is None


def test_wordpress_destino_has_no_social_text(client: TestClient) -> None:
    _ia("x")
    sid, did = _destino(client, "wordpress")

    assert (
        client.post(f"/publication-requests/{sid}/destinos/{did}/texto-ia", json={}).status_code
        == 422
    )


def test_operator_can_edit_but_not_exceed_hashtag_limit(client: TestClient) -> None:
    sid, did = _destino(client, "instagram")
    url = f"/publication-requests/{sid}/destinos/{did}/texto-ia"

    ok = client.put(url, json={"texto": "Editado #a #b"})
    too_many = client.put(url, json={"texto": "x #a #b #c #d #e #f"})
    cleared = client.put(url, json={"texto": "  "})

    assert ok.status_code == 200 and ok.json()["texto_ia"] == "Editado #a #b"
    assert too_many.status_code == 422
    assert cleared.json()["texto_ia"] is None
