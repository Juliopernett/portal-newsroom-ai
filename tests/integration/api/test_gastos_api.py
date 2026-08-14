"""Integration tests: POST/GET/PUT/DELETE /gastos."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _gasto_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "descripcion": "PAGO MENSUAL ANTONIO",
        "valor": "350000.00",
        "fecha": "2026-01-31",
    }
    payload.update(overrides)
    return payload


def test_create_gasto_returns_the_persisted_gasto(client: TestClient) -> None:
    response = client.post("/gastos", json=_gasto_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["descripcion"] == "PAGO MENSUAL ANTONIO"
    assert body["valor"] == "350000.00"
    assert body["fecha"] == "2026-01-31"


def test_create_gasto_rejects_empty_descripcion(client: TestClient) -> None:
    response = client.post("/gastos", json=_gasto_payload(descripcion=""))

    assert response.status_code == 422


def test_create_gasto_rejects_negative_valor(client: TestClient) -> None:
    response = client.post("/gastos", json=_gasto_payload(valor="-1"))

    assert response.status_code == 422


def test_list_gastos_returns_an_empty_list_when_none_exist(client: TestClient) -> None:
    response = client.get("/gastos")

    assert response.status_code == 200
    assert response.json() == []


def test_list_gastos_returns_every_registered_gasto(client: TestClient) -> None:
    client.post("/gastos", json=_gasto_payload(descripcion="Gasto 1"))
    client.post("/gastos", json=_gasto_payload(descripcion="Gasto 2"))

    response = client.get("/gastos")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_gasto_corrects_a_field_without_changing_the_id(client: TestClient) -> None:
    gasto_id = client.post("/gastos", json=_gasto_payload()).json()["id"]

    response = client.put(f"/gastos/{gasto_id}", json=_gasto_payload(valor="400000.00"))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == gasto_id
    assert body["valor"] == "400000.00"


def test_update_gasto_returns_404_when_not_found(client: TestClient) -> None:
    response = client.put("/gastos/no-existe", json=_gasto_payload())

    assert response.status_code == 404


def test_delete_gasto_removes_it_from_the_list(client: TestClient) -> None:
    gasto_id = client.post("/gastos", json=_gasto_payload()).json()["id"]

    response = client.delete(f"/gastos/{gasto_id}")

    assert response.status_code == 204
    assert client.get("/gastos").json() == []


def test_delete_gasto_returns_404_when_not_found(client: TestClient) -> None:
    response = client.delete("/gastos/no-existe")

    assert response.status_code == 404
