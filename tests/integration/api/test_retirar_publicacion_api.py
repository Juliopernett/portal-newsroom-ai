"""Integration tests: POST /publication-requests/{id}/destinos/{id}/retirar.

A publication that went out wrong and was taken down by hand must stop
counting against the pauta (cupo back) without deleting its history.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _hoy_fijo(congelar_hoy: None) -> None:
    """Hard-coded 2026-07/08 Pauta dates below assume "today" is mid-August 2026."""


def _pauta(client: TestClient) -> str:
    client_id = client.post(
        "/clients",
        json={"nombre": "Beto Zabaleta", "tipo": "artista", "telefono": "+573001112233"},
    ).json()["id"]
    pauta_id: str = client.post(
        "/pautas",
        json={
            "client_id": client_id,
            "fecha_inicio": "2026-07-30",
            "fecha_fin": "2026-08-30",
            "publicaciones_contratadas": 10,
            "valor_pagado": "500000.00",
            "fecha_pago": "2026-07-30",
        },
    ).json()["id"]
    return pauta_id


def _consumidas(client: TestClient, pauta_id: str) -> int:
    pautas = client.get("/pautas").json()
    return int(next(p for p in pautas if p["id"] == pauta_id)["publicaciones_consumidas"])


def _solicitud_publicada(client: TestClient, pauta_id: str) -> tuple[str, str]:
    solicitud_id = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Gujira del alma"}
    ).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "facebook"}
    ).json()["id"]
    r = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={"url_publicacion": "https://www.facebook.com/reel/879046791957963/"},
    )
    assert r.status_code == 200, r.text
    return solicitud_id, destino_id


def test_retirar_gives_the_cupo_back_and_keeps_the_history(client: TestClient) -> None:
    pauta_id = _pauta(client)
    solicitud_id, destino_id = _solicitud_publicada(client, pauta_id)
    assert _consumidas(client, pauta_id) == 1

    r = client.post(f"/publication-requests/{solicitud_id}/destinos/{destino_id}/retirar")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["estado"] == "cancelado"
    assert body["url_publicacion"] == "https://www.facebook.com/reel/879046791957963/"
    assert body["fecha_publicacion"] is not None  # history kept
    assert _consumidas(client, pauta_id) == 0
    solicitud = next(
        s for s in client.get("/publication-requests").json() if s["id"] == solicitud_id
    )
    assert solicitud["fecha_cierre"] is None
    assert solicitud["estado"] == "recibida"  # never changes estado by itself


def test_retirar_one_destino_keeps_the_cupo_spent_while_another_is_still_published(
    client: TestClient,
) -> None:
    pauta_id = _pauta(client)
    solicitud_id, facebook_id = _solicitud_publicada(client, pauta_id)
    instagram_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{instagram_id}/confirmar-publicacion",
        json={"url_publicacion": "https://www.instagram.com/reel/abc/"},
    )

    client.post(f"/publication-requests/{solicitud_id}/destinos/{facebook_id}/retirar")

    assert _consumidas(client, pauta_id) == 1  # Instagram is still a real publication


def test_retirar_rejects_a_destino_that_was_never_published(client: TestClient) -> None:
    pauta_id = _pauta(client)
    solicitud_id = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Anuncio"}
    ).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]

    r = client.post(f"/publication-requests/{solicitud_id}/destinos/{destino_id}/retirar")

    assert r.status_code == 422


def test_retirar_returns_404_for_unknown_solicitud_or_destino(client: TestClient) -> None:
    assert client.post("/publication-requests/nope/destinos/nope/retirar").status_code == 404
    pauta_id = _pauta(client)
    solicitud_id, _ = _solicitud_publicada(client, pauta_id)
    assert (
        client.post(f"/publication-requests/{solicitud_id}/destinos/nope/retirar").status_code
        == 404
    )


def test_retirar_requires_authentication(unauthenticated_client: TestClient) -> None:
    r = unauthenticated_client.post("/publication-requests/x/destinos/y/retirar")
    assert r.status_code == 401
