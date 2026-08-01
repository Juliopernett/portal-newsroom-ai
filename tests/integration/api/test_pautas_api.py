"""Integration tests: POST /pautas, GET /pautas/{id}, GET /pautas."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_client(client: TestClient) -> str:
    response = client.post(
        "/clients",
        json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "+573001112233"},
    )
    id_: str = response.json()["id"]
    return id_


def _pauta_payload(client_id: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "client_id": client_id,
        "fecha_inicio": "2026-07-30",
        "fecha_fin": "2026-08-30",
        "publicaciones_contratadas": 10,
        "valor_pagado": "500000.00",
        "fecha_pago": "2026-07-30",
    }
    payload.update(overrides)
    return payload


def test_create_pauta_returns_computed_quota_fields(client: TestClient) -> None:
    client_id = _create_client(client)

    response = client.post("/pautas", json=_pauta_payload(client_id))

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["publicaciones_consumidas"] == 0
    assert body["publicaciones_restantes"] == 10
    assert body["cuota_agotada"] is False


def test_create_pauta_rejects_end_date_not_after_start_date(client: TestClient) -> None:
    client_id = _create_client(client)

    response = client.post(
        "/pautas",
        json=_pauta_payload(client_id, fecha_inicio="2026-08-30", fecha_fin="2026-08-30"),
    )

    assert response.status_code == 422
    assert "fecha_fin" in response.json()["detail"]


def test_create_pauta_rejects_non_positive_publicaciones_contratadas(client: TestClient) -> None:
    client_id = _create_client(client)

    response = client.post("/pautas", json=_pauta_payload(client_id, publicaciones_contratadas=0))

    assert response.status_code == 422


def test_create_pauta_rejects_an_unknown_client_id(client: TestClient) -> None:
    response = client.post("/pautas", json=_pauta_payload("no-existe"))

    assert response.status_code == 400


def test_get_pauta_returns_404_when_not_found(client: TestClient) -> None:
    response = client.get("/pautas/no-existe")

    assert response.status_code == 404


def test_get_pauta_returns_the_persisted_pauta(client: TestClient) -> None:
    client_id = _create_client(client)
    pauta_id = client.post("/pautas", json=_pauta_payload(client_id)).json()["id"]

    response = client.get(f"/pautas/{pauta_id}")

    assert response.status_code == 200
    assert response.json()["id"] == pauta_id


def test_list_pautas_returns_an_empty_list_when_none_exist(client: TestClient) -> None:
    response = client.get("/pautas")

    assert response.status_code == 200
    assert response.json() == []


def test_list_pautas_includes_computed_quota_fields(client: TestClient) -> None:
    client_id = _create_client(client)
    client.post("/pautas", json=_pauta_payload(client_id))

    response = client.get("/pautas")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["publicaciones_restantes"] == 10
