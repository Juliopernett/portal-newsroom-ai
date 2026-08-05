"""Integration tests: POST/GET /publication-requests, POST /{id}/publish, /link-pauta."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_client_and_pauta(client: TestClient) -> str:
    client_id = client.post(
        "/clients",
        json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "+573001112233"},
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
    return pauta_id


def test_create_publication_request_without_a_pauta(client: TestClient) -> None:
    """Sprint 3B.1: a RECIBIDA request can exist with pauta_id=None."""
    response = client.post("/publication-requests", json={"texto": "Anuncio de nueva canción"})

    assert response.status_code == 201
    body = response.json()
    assert body["pauta_id"] is None
    assert body["estado"] == "recibida"


def test_create_publication_request_linked_to_a_pauta(client: TestClient) -> None:
    pauta_id = _create_client_and_pauta(client)

    response = client.post("/publication-requests", json={"pauta_id": pauta_id, "texto": "Anuncio"})

    assert response.status_code == 201
    assert response.json()["pauta_id"] == pauta_id


def test_create_publication_request_rejects_empty_texto(client: TestClient) -> None:
    response = client.post("/publication-requests", json={"texto": ""})

    assert response.status_code == 422


def test_create_publication_request_rejects_an_unknown_pauta_id(client: TestClient) -> None:
    response = client.post(
        "/publication-requests", json={"pauta_id": "no-existe", "texto": "Anuncio"}
    )

    assert response.status_code == 400


def test_publish_returns_404_when_not_found(client: TestClient) -> None:
    response = client.post("/publication-requests/no-existe/publish")

    assert response.status_code == 404


def test_publish_rejects_a_request_without_a_pauta(client: TestClient) -> None:
    """Sprint 3B.1's core invariant, enforced through the API too."""
    solicitud_id = client.post("/publication-requests", json={"texto": "Sin pauta todavía"}).json()[
        "id"
    ]

    response = client.post(f"/publication-requests/{solicitud_id}/publish")

    assert response.status_code == 422
    assert "pauta_id" in response.json()["detail"]


def test_full_flow_create_publish_and_check_remaining_quota(client: TestClient) -> None:
    """The Sprint 3B Definición de Terminado scenario, end to end over HTTP."""
    pauta_id = _create_client_and_pauta(client)

    solicitud_ids = [
        client.post(
            "/publication-requests", json={"pauta_id": pauta_id, "texto": f"Anuncio {n}"}
        ).json()["id"]
        for n in range(3)
    ]

    for solicitud_id in solicitud_ids[:2]:
        response = client.post(f"/publication-requests/{solicitud_id}/publish")
        assert response.status_code == 200
        assert response.json()["estado"] == "publicada"

    estado = client.get(f"/pautas/{pauta_id}").json()
    assert estado["publicaciones_consumidas"] == 2
    assert estado["publicaciones_restantes"] == 8


def test_list_publication_requests_returns_everything_by_default(client: TestClient) -> None:
    pauta_id = _create_client_and_pauta(client)
    solicitud_id = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Anuncio"}
    ).json()["id"]
    client.post(f"/publication-requests/{solicitud_id}/publish")

    response = client.get("/publication-requests")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["estado"] == "publicada"


def test_list_publication_requests_filters_by_estado(client: TestClient) -> None:
    pauta_id = _create_client_and_pauta(client)
    a_publicar = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Se publica"}
    ).json()["id"]
    client.post("/publication-requests", json={"pauta_id": pauta_id, "texto": "Sigue pendiente"})
    client.post(f"/publication-requests/{a_publicar}/publish")

    response = client.get("/publication-requests", params={"estado": "recibida"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["texto"] == "Sigue pendiente"


def test_list_publication_requests_orders_recibida_by_prioridad_then_peso_comercial(
    client: TestClient,
) -> None:
    client_id = client.post(
        "/clients", json={"nombre": "Cliente Alto Valor", "tipo": "artista", "telefono": "300"}
    ).json()["id"]
    pauta_alto = client.post(
        "/pautas",
        json={
            "client_id": client_id,
            "fecha_inicio": "2026-07-30",
            "fecha_fin": "2026-08-30",
            "publicaciones_contratadas": 1,
            "valor_pagado": "500000.00",
            "fecha_pago": "2026-07-30",
        },
    ).json()["id"]
    pauta_bajo = client.post(
        "/pautas",
        json={
            "client_id": client_id,
            "fecha_inicio": "2026-07-30",
            "fecha_fin": "2026-08-30",
            "publicaciones_contratadas": 1,
            "valor_pagado": "10000.00",
            "fecha_pago": "2026-07-30",
        },
    ).json()["id"]

    # Llega primero la de bajo peso comercial, despues la de alto.
    client.post("/publication-requests", json={"pauta_id": pauta_bajo, "texto": "Bajo valor"})
    client.post("/publication-requests", json={"pauta_id": pauta_alto, "texto": "Alto valor"})

    response = client.get("/publication-requests", params={"estado": "recibida"})

    assert response.status_code == 200
    textos = [s["texto"] for s in response.json()]
    # Peso comercial le gana al orden de llegada.
    assert textos == ["Alto valor", "Bajo valor"]


def test_list_publication_requests_rejects_an_invalid_estado(client: TestClient) -> None:
    response = client.get("/publication-requests", params={"estado": "no-existe"})

    assert response.status_code == 422


def test_link_pauta_sets_pauta_id_without_publishing(client: TestClient) -> None:
    pauta_id = _create_client_and_pauta(client)
    solicitud_id = client.post(
        "/publication-requests", json={"texto": "Llegó sin saber de quién era"}
    ).json()["id"]

    response = client.post(
        f"/publication-requests/{solicitud_id}/link-pauta", json={"pauta_id": pauta_id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pauta_id"] == pauta_id
    assert body["estado"] == "recibida"


def test_link_pauta_returns_404_when_request_not_found(client: TestClient) -> None:
    pauta_id = _create_client_and_pauta(client)

    response = client.post(
        "/publication-requests/no-existe/link-pauta", json={"pauta_id": pauta_id}
    )

    assert response.status_code == 404


def test_link_pauta_rejects_an_unknown_pauta_id(client: TestClient) -> None:
    solicitud_id = client.post("/publication-requests", json={"texto": "Sin pauta todavía"}).json()[
        "id"
    ]

    response = client.post(
        f"/publication-requests/{solicitud_id}/link-pauta", json={"pauta_id": "no-existe"}
    )

    assert response.status_code == 400


def test_edit_updates_texto_on_a_recibida_request(client: TestClient) -> None:
    solicitud_id = client.post(
        "/publication-requests", json={"texto": "Texto con un typo"}
    ).json()["id"]

    response = client.patch(
        f"/publication-requests/{solicitud_id}", json={"texto": "Texto corregido"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["texto"] == "Texto corregido"
    assert body["estado"] == "recibida"


def test_edit_updates_prioridad_manual_only(client: TestClient) -> None:
    solicitud_id = client.post(
        "/publication-requests", json={"texto": "Anuncio"}
    ).json()["id"]

    response = client.patch(
        f"/publication-requests/{solicitud_id}", json={"prioridad_manual": True}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["prioridad_manual"] is True
    assert body["texto"] == "Anuncio"


def test_edit_returns_404_when_not_found(client: TestClient) -> None:
    response = client.patch("/publication-requests/no-existe", json={"texto": "Nuevo texto"})

    assert response.status_code == 404


def test_edit_rejects_a_published_request(client: TestClient) -> None:
    pauta_id = _create_client_and_pauta(client)
    solicitud_id = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Anuncio"}
    ).json()["id"]
    client.post(f"/publication-requests/{solicitud_id}/publish")

    response = client.patch(
        f"/publication-requests/{solicitud_id}", json={"texto": "Ya se publicó, muy tarde"}
    )

    assert response.status_code == 422


def test_edit_rejects_an_empty_texto(client: TestClient) -> None:
    solicitud_id = client.post(
        "/publication-requests", json={"texto": "Anuncio"}
    ).json()["id"]

    response = client.patch(f"/publication-requests/{solicitud_id}", json={"texto": ""})

    assert response.status_code == 422


def test_full_flow_receive_without_pauta_link_then_publish(client: TestClient) -> None:
    """The operational gap the UX review flagged, closed end to end over HTTP."""
    pauta_id = _create_client_and_pauta(client)
    solicitud_id = client.post(
        "/publication-requests", json={"texto": "Llegó de un número desconocido"}
    ).json()["id"]

    # sin pauta, publicar debe fallar
    assert client.post(f"/publication-requests/{solicitud_id}/publish").status_code == 422

    link_response = client.post(
        f"/publication-requests/{solicitud_id}/link-pauta", json={"pauta_id": pauta_id}
    )
    assert link_response.status_code == 200
    assert link_response.json()["pauta_id"] == pauta_id

    publish_response = client.post(f"/publication-requests/{solicitud_id}/publish")
    assert publish_response.status_code == 200
    assert publish_response.json()["estado"] == "publicada"

    estado = client.get(f"/pautas/{pauta_id}").json()
    assert estado["publicaciones_consumidas"] == 1
    assert estado["publicaciones_restantes"] == 9
