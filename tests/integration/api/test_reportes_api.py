"""Integration tests: GET /reportes/rentabilidad.csv, /pautas.csv, /gastos.csv.

Business rules (rentabilidad math, pauta vigente/restantes) are already
covered at the unit level — these tests only confirm the routes are wired,
protected, and return a real downloadable CSV (`Content-Disposition`,
correct rows, `desde`/`hasta` filtering).
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


def _create_gasto(client: TestClient, **overrides: object) -> str:
    payload: dict[str, object] = {
        "descripcion": "PAGO MENSUAL ANTONIO",
        "valor": "350000.00",
        "fecha": "2026-01-31",
    }
    payload.update(overrides)
    response = client.post("/gastos", json=payload)
    id_: str = response.json()["id"]
    return id_


def test_reportes_routes_require_authentication(unauthenticated_client: TestClient) -> None:
    for path in ("/reportes/rentabilidad.csv", "/reportes/pautas.csv", "/reportes/gastos.csv"):
        assert unauthenticated_client.get(path).status_code == 401


def test_rentabilidad_csv_is_a_downloadable_file_with_the_requested_range(
    client: TestClient,
) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id, fecha_pago="2026-06-15", valor_pagado="500000.00")
    _create_gasto(client, fecha="2026-06-20", valor="100000.00")

    response = client.get(
        "/reportes/rentabilidad.csv", params={"desde": "2026-06-01", "hasta": "2026-06-30"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="rentabilidad_mensual.csv"' in response.headers["content-disposition"]
    body = response.text
    assert body.startswith("﻿Mes,Ingresos,Gastos,Rentabilidad")
    assert "2026-06,500000.00,100000.00,400000.00" in body
    assert body.count("\r\n") == 2  # encabezado + una sola fila de datos (un mes en el rango)


def test_pautas_csv_defaults_to_full_history_ordered_by_fecha_inicio(client: TestClient) -> None:
    client_id = _create_client(client, nombre="Peter Manjarrés")
    _create_pauta(client, client_id, fecha_inicio="2026-03-01", fecha_fin="2026-03-10")
    _create_pauta(client, client_id, fecha_inicio="2026-01-01", fecha_fin="2026-01-10")

    response = client.get("/reportes/pautas.csv")

    assert response.status_code == 200
    assert 'filename="pautas.csv"' in response.headers["content-disposition"]
    lines = response.text.lstrip("﻿").splitlines()
    assert lines[1].startswith("Peter Manjarrés,Individual,2026-01-01,2026-01-10")
    assert lines[2].startswith("Peter Manjarrés,Individual,2026-03-01,2026-03-10")


def test_pautas_csv_filters_by_fecha_inicio_range(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id, fecha_inicio="2026-01-01", fecha_fin="2026-01-10")
    _create_pauta(client, client_id, fecha_inicio="2026-06-01", fecha_fin="2026-06-10")

    response = client.get(
        "/reportes/pautas.csv", params={"desde": "2026-05-01", "hasta": "2026-07-01"}
    )

    lines = response.text.lstrip("﻿").splitlines()
    assert len(lines) == 2  # encabezado + una sola pauta en el rango
    assert "2026-06-01" in lines[1]


def test_gastos_csv_defaults_to_full_history_ordered_by_fecha(client: TestClient) -> None:
    _create_gasto(client, descripcion="Gasto de marzo", fecha="2026-03-01")
    _create_gasto(client, descripcion="Gasto de enero", fecha="2026-01-01")

    response = client.get("/reportes/gastos.csv")

    assert response.status_code == 200
    assert 'filename="gastos.csv"' in response.headers["content-disposition"]
    lines = response.text.lstrip("﻿").splitlines()
    assert lines[0] == "Fecha,Descripción,Valor"
    assert lines[1].startswith("2026-01-01,Gasto de enero")
    assert lines[2].startswith("2026-03-01,Gasto de marzo")


def test_gastos_csv_filters_by_fecha_range(client: TestClient) -> None:
    _create_gasto(client, fecha="2026-01-01")
    _create_gasto(client, fecha="2026-06-01")

    response = client.get(
        "/reportes/gastos.csv", params={"desde": "2026-05-01", "hasta": "2026-07-01"}
    )

    lines = response.text.lstrip("﻿").splitlines()
    assert len(lines) == 2
    assert lines[1].startswith("2026-06-01")
