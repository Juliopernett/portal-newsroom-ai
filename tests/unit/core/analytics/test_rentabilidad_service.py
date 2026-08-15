"""Unit tests for rentabilidad_mensual and meses_atras."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.analytics.rentabilidad_service import meses_atras, rentabilidad_mensual
from core.entities.gasto import Gasto
from core.entities.pauta import Pauta


def _pauta(**overrides: object) -> Pauta:
    defaults: dict[str, object] = {
        "client_id": "client-1",
        "fecha_inicio": date(2026, 1, 1),
        "fecha_fin": date(2026, 1, 31),
        "publicaciones_contratadas": 1,
        "valor_pagado": Decimal("100000"),
        "fecha_pago": date(2026, 1, 15),
    }
    defaults.update(overrides)
    return Pauta(**defaults)


def _gasto(**overrides: object) -> Gasto:
    defaults: dict[str, object] = {
        "descripcion": "Gasto de prueba",
        "valor": Decimal("30000"),
        "fecha": date(2026, 1, 15),
    }
    defaults.update(overrides)
    return Gasto(**defaults)


def test_meses_atras_within_the_same_year() -> None:
    assert meses_atras(2026, 8, 3) == (2026, 5)


def test_meses_atras_crosses_a_year_boundary() -> None:
    assert meses_atras(2026, 1, 1) == (2025, 12)


def test_meses_atras_crosses_multiple_years() -> None:
    assert meses_atras(2026, 3, 15) == (2024, 12)


def test_rentabilidad_mensual_returns_every_month_in_range_oldest_first() -> None:
    resultado = rentabilidad_mensual([], [], desde=date(2026, 1, 1), hasta=date(2026, 3, 31))

    assert [(item.anio, item.mes) for item in resultado] == [
        (2026, 1),
        (2026, 2),
        (2026, 3),
    ]


def test_rentabilidad_mensual_handles_a_single_month_range() -> None:
    resultado = rentabilidad_mensual([], [], desde=date(2026, 1, 1), hasta=date(2026, 1, 31))

    assert [(item.anio, item.mes) for item in resultado] == [(2026, 1)]


def test_rentabilidad_mensual_handles_a_range_crossing_a_year_boundary() -> None:
    resultado = rentabilidad_mensual([], [], desde=date(2025, 12, 1), hasta=date(2026, 1, 31))

    assert [(item.anio, item.mes) for item in resultado] == [(2025, 12), (2026, 1)]


def test_rentabilidad_mensual_sums_ingresos_by_fecha_pago_month() -> None:
    pautas = [
        _pauta(fecha_pago=date(2026, 1, 10), valor_pagado=Decimal("100000")),
        _pauta(fecha_pago=date(2026, 1, 20), valor_pagado=Decimal("50000")),
    ]

    resultado = rentabilidad_mensual(pautas, [], desde=date(2026, 1, 1), hasta=date(2026, 1, 31))

    assert resultado[0].ingresos == Decimal("150000")


def test_rentabilidad_mensual_sums_gastos_by_fecha_month() -> None:
    gastos = [
        _gasto(fecha=date(2026, 1, 5), valor=Decimal("30000")),
        _gasto(fecha=date(2026, 1, 25), valor=Decimal("20000")),
    ]

    resultado = rentabilidad_mensual([], gastos, desde=date(2026, 1, 1), hasta=date(2026, 1, 31))

    assert resultado[0].gastos == Decimal("50000")


def test_rentabilidad_mensual_computes_rentabilidad_as_ingresos_minus_gastos() -> None:
    pautas = [_pauta(fecha_pago=date(2026, 1, 10), valor_pagado=Decimal("100000"))]
    gastos = [_gasto(fecha=date(2026, 1, 5), valor=Decimal("30000"))]

    resultado = rentabilidad_mensual(
        pautas, gastos, desde=date(2026, 1, 1), hasta=date(2026, 1, 31)
    )

    assert resultado[0].rentabilidad == Decimal("70000")


def test_rentabilidad_mensual_includes_empty_months_at_zero() -> None:
    resultado = rentabilidad_mensual([], [], desde=date(2026, 1, 1), hasta=date(2026, 2, 28))

    assert all(item.ingresos == Decimal("0") and item.gastos == Decimal("0") for item in resultado)


def test_rentabilidad_mensual_excludes_pautas_paid_outside_the_range() -> None:
    pautas = [_pauta(fecha_pago=date(2025, 12, 31), valor_pagado=Decimal("100000"))]

    resultado = rentabilidad_mensual(pautas, [], desde=date(2026, 1, 1), hasta=date(2026, 1, 31))

    assert resultado[0].ingresos == Decimal("0")
