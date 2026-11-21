"""Integration tests: GET /deudores (clients who owe money, grouped)."""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from core.clock import now_local


def _cliente(client: TestClient, nombre: str) -> str:
    r = client.post(
        "/clients", json={"nombre": nombre, "tipo": "artista", "telefono": "+573001112233"}
    )
    id_: str = r.json()["id"]
    return id_


def _pauta(client: TestClient, client_id: str, saldo: str, dias_atras: int) -> None:
    hoy = now_local().date()
    r = client.post(
        "/pautas",
        json={
            "client_id": client_id,
            "fecha_inicio": str(hoy - timedelta(days=dias_atras)),
            "fecha_fin": str(hoy + timedelta(days=60)),
            "publicaciones_contratadas": 10,
            "valor_pagado": "500000.00",
            "fecha_pago": str(hoy - timedelta(days=dias_atras)),
            "saldo_pendiente": saldo,
        },
    )
    assert r.status_code == 201, r.text


def test_requires_authentication(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get("/deudores").status_code == 401


def test_empty_when_nobody_owes(client: TestClient) -> None:
    body = client.get("/deudores").json()
    assert body == {"total_por_cobrar": "0", "cantidad": 0, "deudores": []}


def test_lists_debtors_grouped_with_total_and_age(client: TestClient) -> None:
    ana, beto, al_dia = (
        _cliente(client, "Ana"),
        _cliente(client, "Beto"),
        _cliente(client, "Al día"),
    )
    _pauta(client, ana, "100000", 10)
    _pauta(client, ana, "300000", 45)
    _pauta(client, beto, "900000", 5)
    _pauta(client, al_dia, "0", 5)

    body = client.get("/deudores").json()

    assert body["cantidad"] == 2
    assert float(body["total_por_cobrar"]) == 1_300_000
    primero, segundo = body["deudores"]
    assert primero["cliente"]["nombre"] == "Beto" and float(primero["total_pendiente"]) == 900_000
    assert segundo["cliente"]["nombre"] == "Ana"
    assert segundo["dias_mas_antiguo"] == 45
    assert [s["dias_desde_pago"] for s in segundo["saldos"]] == [45, 10]
    assert segundo["cliente"]["telefono"] == "+573001112233"
