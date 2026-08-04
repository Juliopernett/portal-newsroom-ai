"""Integration tests: POST /clients, GET /clients, PUT /clients/{id}."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_client_returns_201_with_generated_id(client: TestClient) -> None:
    response = client.post(
        "/clients",
        json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "+573001112233"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["nombre"] == "Silvestre Dangond"
    assert body["tipo"] == "artista"
    assert body["instagram"] is None


def test_create_client_rejects_empty_nombre(client: TestClient) -> None:
    response = client.post(
        "/clients", json={"nombre": "", "tipo": "artista", "telefono": "+573001112233"}
    )

    assert response.status_code == 422
    assert "nombre" in response.json()["detail"]


def test_create_client_rejects_invalid_tipo(client: TestClient) -> None:
    response = client.post(
        "/clients", json={"nombre": "X", "tipo": "no-existe", "telefono": "+573001112233"}
    )

    assert response.status_code == 422


def test_create_client_rejects_missing_required_field(client: TestClient) -> None:
    response = client.post("/clients", json={"nombre": "X", "tipo": "artista"})

    assert response.status_code == 422


def test_list_clients_returns_an_empty_list_when_none_exist(client: TestClient) -> None:
    response = client.get("/clients")

    assert response.status_code == 200
    assert response.json() == []


def test_list_clients_returns_every_created_client(client: TestClient) -> None:
    client.post(
        "/clients",
        json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "+573001112233"},
    )
    client.post(
        "/clients",
        json={"nombre": "Peter Manjarrés", "tipo": "artista", "telefono": "+573004445566"},
    )

    response = client.get("/clients")

    assert response.status_code == 200
    nombres = {c["nombre"] for c in response.json()}
    assert nombres == {"Silvestre Dangond", "Peter Manjarrés"}


def test_update_client_replaces_editable_fields(client: TestClient) -> None:
    created = client.post(
        "/clients",
        json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "+573001112233"},
    ).json()

    response = client.put(
        f"/clients/{created['id']}",
        json={
            "nombre": "Silvestre Dangond Corregido",
            "tipo": "manager",
            "telefono": "+573009998877",
            "instagram": "@silvestre",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["nombre"] == "Silvestre Dangond Corregido"
    assert body["tipo"] == "manager"
    assert body["telefono"] == "+573009998877"
    assert body["instagram"] == "@silvestre"


def test_update_client_persists_across_requests(client: TestClient) -> None:
    created = client.post(
        "/clients",
        json={"nombre": "Nombre Original", "tipo": "artista", "telefono": "+573001112233"},
    ).json()

    client.put(
        f"/clients/{created['id']}",
        json={"nombre": "Nombre Corregido", "tipo": "artista", "telefono": "+573001112233"},
    )

    response = client.get("/clients")

    nombres = {c["nombre"] for c in response.json()}
    assert nombres == {"Nombre Corregido"}


def test_update_client_returns_404_when_not_found(client: TestClient) -> None:
    response = client.put(
        "/clients/no-existe",
        json={"nombre": "X", "tipo": "artista", "telefono": "+573001112233"},
    )

    assert response.status_code == 404


def test_update_client_rejects_empty_nombre(client: TestClient) -> None:
    created = client.post(
        "/clients",
        json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "+573001112233"},
    ).json()

    response = client.put(
        f"/clients/{created['id']}",
        json={"nombre": "", "tipo": "artista", "telefono": "+573001112233"},
    )

    assert response.status_code == 422
