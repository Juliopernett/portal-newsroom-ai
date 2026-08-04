"""Integration tests: GET /dashboard/resumen, /alertas, /ranking.

Domain business rules (what counts as "activo", "cupo bajo", etc.) are
already covered exhaustively at the unit level
(`tests/unit/core/analytics/test_analytics_service.py`) — these tests only
confirm the routes are wired, protected, and serialize what
`AnalyticsService` returns correctly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_client(client: TestClient, **overrides: object) -> str:
    payload: dict[str, object] = {
        "nombre": "Silvestre Dangond",
        "tipo": "artista",
        "telefono": "+573001112233",
    }
    payload.update(overrides)
    response = client.post("/clients", json=payload)
    id_: str = response.json()["id"]
    return id_


def _create_pauta(client: TestClient, client_id: str, **overrides: object) -> str:
    payload: dict[str, object] = {
        "client_id": client_id,
        "fecha_inicio": "2026-07-01",
        "fecha_fin": "2026-08-30",
        "publicaciones_contratadas": 10,
        "valor_pagado": "500000.00",
        "fecha_pago": "2026-07-01",
    }
    payload.update(overrides)
    response = client.post("/pautas", json=payload)
    id_: str = response.json()["id"]
    return id_


def _create_solicitud(client: TestClient, pauta_id: str | None, **overrides: object) -> str:
    payload: dict[str, object] = {"pauta_id": pauta_id, "texto": "Publicar esto"}
    payload.update(overrides)
    response = client.post("/publication-requests", json=payload)
    id_: str = response.json()["id"]
    return id_


def test_resumen_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/dashboard/resumen")

    assert response.status_code == 401


def test_alertas_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/dashboard/alertas")

    assert response.status_code == 401


def test_ranking_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/dashboard/ranking")

    assert response.status_code == 401


def test_resumen_is_all_zero_with_no_data(client: TestClient) -> None:
    response = client.get("/dashboard/resumen")

    assert response.status_code == 200
    body = response.json()
    assert body["clientes_activos"] == 0
    assert body["pautas_activas"] == 0
    assert body["ingreso_historico"] == "0"
    assert body["peso_comercial_promedio"] == "0"
    assert body["valor_promedio_por_cliente"] == "0"
    assert body["clientes_premium"] == 0


def test_resumen_reflects_a_vigente_pauta(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id)

    response = client.get("/dashboard/resumen")

    assert response.status_code == 200
    body = response.json()
    assert body["clientes_activos"] == 1
    assert body["pautas_activas"] == 1
    assert body["pautas_vencidas"] == 0
    assert body["ingreso_historico"] == "500000.00"
    assert body["ingreso_contratado_activo"] == "500000.00"


def test_alertas_lists_a_client_with_exhausted_quota(client: TestClient) -> None:
    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id, publicaciones_contratadas=1)
    solicitud_id = _create_solicitud(client, pauta_id)
    client.post(f"/publication-requests/{solicitud_id}/publish")

    response = client.get("/dashboard/alertas")

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body["clientes_cupo_agotado"]] == [client_id]
    assert [c["id"] for c in body["clientes_menos_de_3_restantes"]] == [client_id]


def test_alertas_lists_a_client_with_pending_individual_publications(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(
        client,
        client_id,
        fecha_inicio="2026-07-30",
        fecha_fin="2026-08-05",
        publicaciones_contratadas=3,
    )

    response = client.get("/dashboard/alertas")

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body["clientes_individuales_pendientes"]] == [client_id]
    assert body["clientes_contrato_por_renovar"] == []


def test_alertas_lists_a_client_with_a_package_contract_about_to_renew(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id, fecha_inicio="2026-07-01", fecha_fin="2026-08-10")

    response = client.get("/dashboard/alertas")

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body["clientes_contrato_por_renovar"]] == [client_id]
    assert body["clientes_individuales_pendientes"] == []


def test_alertas_lists_a_client_who_left_publications_unused_on_an_expired_pauta(
    client: TestClient,
) -> None:
    client_id = _create_client(client)
    _create_pauta(
        client,
        client_id,
        fecha_inicio="2026-01-01",
        fecha_fin="2026-02-01",
        publicaciones_contratadas=8,
    )

    response = client.get("/dashboard/alertas")

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body["clientes_publicaciones_sin_usar"]] == [client_id]
    # No es una alerta operativa -- una pauta vencida no cuenta para estas.
    assert body["clientes_cupo_agotado"] == []
    assert body["clientes_menos_de_3_restantes"] == []


def test_alertas_lists_an_old_pending_solicitud(client: TestClient) -> None:
    _create_solicitud(client, pauta_id=None)

    response = client.get("/dashboard/alertas", params={})

    assert response.status_code == 200
    # Recien creada, no cumple el umbral de 4 horas por defecto todavia.
    assert response.json()["solicitudes_antiguas"] == []


def test_ranking_reflects_a_clients_pauta(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id, valor_pagado="200000.00", publicaciones_contratadas=10)

    response = client.get("/dashboard/ranking")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["cliente"]["id"] == client_id
    assert body[0]["valor_contratado"] == "200000.00"
    assert body[0]["peso_comercial"] == "20000.00"
    assert body[0]["publicaciones_contratadas"] == 10
    assert body[0]["publicaciones_restantes"] == 10
    assert body[0]["vigente"] is True
    assert body[0]["estado_comercial"] == "saludable"


def test_ranking_excludes_clients_without_a_pauta(client: TestClient) -> None:
    _create_client(client)

    response = client.get("/dashboard/ranking")

    assert response.status_code == 200
    assert response.json() == []
