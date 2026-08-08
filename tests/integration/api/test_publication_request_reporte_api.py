"""Integration tests: GET /publication-requests/{id}/reporte (Sprint 4A, Incremento 6)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_client_and_pauta(
    client: TestClient, nombre: str = "Silvestre Dangond"
) -> tuple[str, str]:
    client_id = client.post(
        "/clients", json={"nombre": nombre, "tipo": "artista", "telefono": "+573001112233"}
    ).json()["id"]
    pauta_response = client.post(
        "/pautas",
        json={
            "client_id": client_id,
            "fecha_inicio": "2026-07-30",
            "fecha_fin": "2026-08-30",
            "publicaciones_contratadas": 10,
            "valor_pagado": "500000.00",
            "fecha_pago": "2026-07-30",
        },
    )
    pauta_id: str = pauta_response.json()["id"]
    return client_id, pauta_id


def test_reporte_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.get("/publication-requests/no-existe/reporte")

    assert response.status_code == 404


def test_reporte_for_a_plain_solicitud_with_no_destinos(client: TestClient) -> None:
    solicitud_id = client.post(
        "/publication-requests", json={"titulo": "Prueba", "texto": "Anuncio"}
    ).json()["id"]

    response = client.get(f"/publication-requests/{solicitud_id}/reporte")

    assert response.status_code == 200
    body = response.json()
    assert body["publication_request_id"] == solicitud_id
    assert body["titulo"] == "Prueba"
    assert body["texto"] == "Anuncio"
    assert body["cliente_nombre"] is None
    assert body["pauta_id"] is None
    assert body["completa"] is False
    assert body["pauta_consumida"] is False
    assert body["destinos"] == []


def test_reporte_instagram_only_completa_but_no_pauta_consumida(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Solo Instagram"}).json()[
        "id"
    ]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"}
    ).json()["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/reporte"},
    )

    response = client.get(f"/publication-requests/{solicitud_id}/reporte")

    assert response.status_code == 200
    body = response.json()
    assert body["completa"] is True
    assert body["pauta_consumida"] is False
    assert len(body["destinos"]) == 1
    destino = body["destinos"][0]
    assert destino["canal"] == "instagram"
    assert destino["estado"] == "publicado"
    assert destino["enlace"] == "https://instagram.com/p/reporte"
    assert destino["fecha_publicacion"] is not None


def test_reporte_includes_cliente_nombre_and_pauta_consumida_via_publish(
    client: TestClient,
) -> None:
    _client_id, pauta_id = _create_client_and_pauta(client, nombre="Andrés Ariza")
    solicitud_id = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Anuncio"}
    ).json()["id"]
    client.post(f"/publication-requests/{solicitud_id}/publish")

    response = client.get(f"/publication-requests/{solicitud_id}/reporte")

    assert response.status_code == 200
    body = response.json()
    assert body["cliente_nombre"] == "Andrés Ariza"
    assert body["pauta_id"] == pauta_id
    assert body["completa"] is True
    assert body["pauta_consumida"] is True
    assert body["fecha_cierre"] is not None
    assert len(body["destinos"]) == 1
    assert body["destinos"][0]["canal"] == "wordpress"
    assert body["destinos"][0]["estado"] == "publicado"


def test_reporte_multi_destino_not_complete_shows_pending_destino_with_no_enlace(
    client: TestClient,
) -> None:
    _client_id, pauta_id = _create_client_and_pauta(client)
    solicitud_id = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Multi-destino"}
    ).json()["id"]
    client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "facebook"})
    client.post(f"/publication-requests/{solicitud_id}/publish")

    response = client.get(f"/publication-requests/{solicitud_id}/reporte")

    assert response.status_code == 200
    body = response.json()
    assert body["completa"] is False
    assert body["pauta_consumida"] is False
    canales = {d["canal"]: d for d in body["destinos"]}
    assert canales["wordpress"]["estado"] == "publicado"
    assert canales["facebook"]["estado"] == "pendiente"
    assert canales["facebook"]["enlace"] is None
