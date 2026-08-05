"""Integration tests: GET /insights/{salud-clientes,centro-alertas,riesgo-abandono,dormidos,oportunidades}.

Domain business rules (score weights, inactivity thresholds, renewal-chain
detection) are already covered exhaustively at the unit level
(`tests/unit/core/analytics/test_decision_engine.py`) — these tests only
confirm the routes are wired, protected, and serialize what
`DecisionEngineService` returns correctly.
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


def test_salud_clientes_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/insights/salud-clientes")

    assert response.status_code == 401


def test_centro_alertas_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/insights/centro-alertas")

    assert response.status_code == 401


def test_riesgo_abandono_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/insights/riesgo-abandono")

    assert response.status_code == 401


def test_dormidos_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/insights/dormidos")

    assert response.status_code == 401


def test_oportunidades_requires_authentication(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/insights/oportunidades")

    assert response.status_code == 401


def test_salud_clientes_is_empty_with_no_data(client: TestClient) -> None:
    response = client.get("/insights/salud-clientes")

    assert response.status_code == 200
    assert response.json() == []


def test_salud_clientes_scores_a_client_with_a_vigente_pauta(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id)

    response = client.get("/insights/salud-clientes")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["cliente"]["id"] == client_id
    assert 0 <= body[0]["score"] <= 100
    assert 0 <= body[0]["estrellas"] <= 5


def test_centro_alertas_lists_a_client_with_exhausted_quota(client: TestClient) -> None:
    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id, publicaciones_contratadas=1)
    solicitud = client.post(
        "/publication-requests", json={"pauta_id": pauta_id, "texto": "Publicar esto"}
    ).json()
    client.post(f"/publication-requests/{solicitud['id']}/publish")

    response = client.get("/insights/centro-alertas")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["tipo"] == "cupo_agotado"
    assert body[0]["cliente"]["id"] == client_id
    assert body[0]["accion"] == "renovar"


def test_riesgo_abandono_is_empty_with_no_data(client: TestClient) -> None:
    response = client.get("/insights/riesgo-abandono")

    assert response.status_code == 200
    assert response.json() == []


def test_dormidos_is_empty_with_no_data(client: TestClient) -> None:
    response = client.get("/insights/dormidos")

    assert response.status_code == 200
    assert response.json() == []


def test_dormidos_excludes_a_freshly_registered_client_despite_an_expired_pauta(
    client: TestClient,
) -> None:
    """`fecha_registro` is server-assigned at creation time (just now, via this
    same request) — even though the Pauta itself already expired
    (`fecha_fin` in the past), the Client only just "registered" activity,
    nowhere near the 60-day Dormido threshold. A positive Dormidos case
    needs an old `fecha_registro`, which the public API has no way to
    backdate — covered instead at the unit level with an injected clock.
    """
    client_id = _create_client(client)
    _create_pauta(client, client_id, fecha_inicio="2026-01-01", fecha_fin="2026-02-01")

    response = client.get("/insights/dormidos")

    assert response.status_code == 200
    assert client_id not in [item["cliente"]["id"] for item in response.json()]


def test_oportunidades_lists_a_client_who_never_contracted_premium(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id)

    response = client.get("/insights/oportunidades")

    assert response.status_code == 200
    tipos = [item["tipo"] for item in response.json() if item["cliente"]["id"] == client_id]
    assert "nunca_premium" in tipos
