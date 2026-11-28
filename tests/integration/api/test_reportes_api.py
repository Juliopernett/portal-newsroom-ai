"""Integration tests: GET /reportes/*.xlsx.

Business rules (rentabilidad math, pauta vigente/restantes) are already
covered at the unit level — these tests only confirm the routes are wired,
protected, and return a real downloadable Excel file (`Content-Disposition`,
typed cells, totals, `desde`/`hasta` filtering).
"""

from __future__ import annotations

import io
from datetime import datetime

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook

_NOMBRES = ("rentabilidad", "pautas", "gastos", "otros-ingresos", "completo")


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


def _descargar(client: TestClient, nombre: str, **params: str) -> Workbook:
    response = client.get(f"/reportes/{nombre}.xlsx", params=params)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return load_workbook(io.BytesIO(response.content))


def _filas(libro: Workbook, hoja: str) -> list[tuple[object, ...]]:
    return [tuple(fila) for fila in libro[hoja].iter_rows(values_only=True)]


def test_reportes_routes_require_authentication(unauthenticated_client: TestClient) -> None:
    for nombre in _NOMBRES:
        assert unauthenticated_client.get(f"/reportes/{nombre}.xlsx").status_code == 401


def test_rentabilidad_has_dates_numbers_and_a_totals_row(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id, fecha_pago="2026-06-15", valor_pagado="500000.00")
    _create_gasto(client, fecha="2026-06-20", valor="100000.00")

    response = client.get(
        "/reportes/rentabilidad.xlsx", params={"desde": "2026-06-01", "hasta": "2026-06-30"}
    )
    assert 'filename="rentabilidad_mensual.xlsx"' in response.headers["content-disposition"]
    libro = load_workbook(io.BytesIO(response.content))

    assert _filas(libro, "Rentabilidad") == [
        ("Mes", "Ingresos", "Gastos", "Rentabilidad"),
        (datetime(2026, 6, 1), 500000, 100000, 400000),
        ("TOTAL", "=SUBTOTAL(109,B2:B2)", "=SUBTOTAL(109,C2:C2)", "=SUBTOTAL(109,D2:D2)"),
    ]
    hoja = libro["Rentabilidad"]
    assert hoja.freeze_panes == "A2"
    assert hoja.auto_filter.ref == "A1:D2"  # the totals row stays out of the filter
    assert "$" in hoja["B2"].number_format
    assert hoja["A1"].fill.fgColor.rgb.endswith("3B5998")


def test_pautas_defaults_to_full_history_ordered_by_fecha_inicio(client: TestClient) -> None:
    client_id = _create_client(client, nombre="Peter Manjarrés")
    _create_pauta(client, client_id, fecha_inicio="2026-03-01", fecha_fin="2026-03-10")
    _create_pauta(client, client_id, fecha_inicio="2026-01-01", fecha_fin="2026-01-10")

    filas = _filas(_descargar(client, "pautas"), "Pautas")

    assert filas[1][:4] == (
        "Peter Manjarrés",
        "Individual",
        datetime(2026, 1, 1),
        datetime(2026, 1, 10),
    )
    assert filas[2][2] == datetime(2026, 3, 1)
    assert filas[3][6] == "=SUBTOTAL(109,G2:G3)"


def test_pautas_filters_by_fecha_inicio_range(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id, fecha_inicio="2026-01-01", fecha_fin="2026-01-10")
    _create_pauta(client, client_id, fecha_inicio="2026-06-01", fecha_fin="2026-06-10")

    libro = _descargar(client, "pautas", desde="2026-05-01", hasta="2026-07-01")

    filas = _filas(libro, "Pautas")
    assert len(filas) == 3  # encabezado + una pauta en el rango + total
    assert filas[1][2] == datetime(2026, 6, 1)


def test_gastos_defaults_to_full_history_ordered_by_fecha(client: TestClient) -> None:
    _create_gasto(client, descripcion="Gasto de marzo", fecha="2026-03-01")
    _create_gasto(client, descripcion="Gasto de enero", fecha="2026-01-01")

    filas = _filas(_descargar(client, "gastos"), "Gastos")

    assert filas[0] == ("Fecha", "Descripción", "Valor")
    assert filas[1] == (datetime(2026, 1, 1), "Gasto de enero", 350000)
    assert filas[2][1] == "Gasto de marzo"


def test_gastos_filters_by_fecha_range(client: TestClient) -> None:
    _create_gasto(client, fecha="2026-01-01")
    _create_gasto(client, fecha="2026-06-01")

    libro = _descargar(client, "gastos", desde="2026-05-01", hasta="2026-07-01")

    filas = _filas(libro, "Gastos")
    assert len(filas) == 3
    assert filas[1][0] == datetime(2026, 6, 1)


def test_typed_text_never_becomes_a_formula(client: TestClient) -> None:
    _create_gasto(client, descripcion='=HYPERLINK("http://example.test","clic")')

    celda = _descargar(client, "gastos")["Gastos"]["B2"]

    assert celda.data_type == "s"
    assert celda.value.startswith("=HYPERLINK")


def test_an_empty_report_has_only_the_header(client: TestClient) -> None:
    assert _filas(_descargar(client, "otros-ingresos"), "Otros ingresos") == [
        ("Fecha", "Origen", "Valor (COP)", "Valor (USD)", "Notas")
    ]


def test_completo_has_one_sheet_per_report_covering_the_whole_history(client: TestClient) -> None:
    client_id = _create_client(client)
    _create_pauta(client, client_id, fecha_pago="2024-03-15", valor_pagado="500000.00")
    _create_gasto(client, fecha="2026-01-31")

    libro = _descargar(client, "completo")

    assert libro.sheetnames == ["Rentabilidad", "Pautas", "Gastos", "Otros ingresos"]
    # older than the 12-month default of the single report
    assert _filas(libro, "Rentabilidad")[1][:2] == (datetime(2024, 3, 1), 500000)


def test_completo_respects_the_date_range(client: TestClient) -> None:
    _create_gasto(client, fecha="2026-01-31")
    _create_gasto(client, fecha="2026-06-20")

    libro = _descargar(client, "completo", desde="2026-06-01", hasta="2026-06-30")

    assert len(_filas(libro, "Rentabilidad")) == 3
    assert len(_filas(libro, "Gastos")) == 3
