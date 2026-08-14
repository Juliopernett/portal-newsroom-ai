"""Unit tests for rentabilidad_mensual."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.analytics.rentabilidad_service import rentabilidad_mensual
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


def test_rentabilidad_mensual_returns_meses_months_oldest_first() -> None:
    resultado = rentabilidad_mensual([], [], meses=3, clock=lambda: date(2026, 3, 15))

    assert [(item.anio, item.mes) for item in resultado] == [
        (2026, 1),
        (2026, 2),
        (2026, 3),
    ]


def test_rentabilidad_mensual_sums_ingresos_by_fecha_pago_month() -> None:
    pautas = [
        _pauta(fecha_pago=date(2026, 1, 10), valor_pagado=Decimal("100000")),
        _pauta(fecha_pago=date(2026, 1, 20), valor_pagado=Decimal("50000")),
    ]

    resultado = rentabilidad_mensual(pautas, [], meses=1, clock=lambda: date(2026, 1, 31))

    assert resultado[0].ingresos == Decimal("150000")


def test_rentabilidad_mensual_sums_gastos_by_fecha_month() -> None:
    gastos = [
        _gasto(fecha=date(2026, 1, 5), valor=Decimal("30000")),
        _gasto(fecha=date(2026, 1, 25), valor=Decimal("20000")),
    ]

    resultado = rentabilidad_mensual([], gastos, meses=1, clock=lambda: date(2026, 1, 31))

    assert resultado[0].gastos == Decimal("50000")


def test_rentabilidad_mensual_computes_rentabilidad_as_ingresos_minus_gastos() -> None:
    pautas = [_pauta(fecha_pago=date(2026, 1, 10), valor_pagado=Decimal("100000"))]
    gastos = [_gasto(fecha=date(2026, 1, 5), valor=Decimal("30000"))]

    resultado = rentabilidad_mensual(pautas, gastos, meses=1, clock=lambda: date(2026, 1, 31))

    assert resultado[0].rentabilidad == Decimal("70000")


def test_rentabilidad_mensual_includes_empty_months_at_zero() -> None:
    resultado = rentabilidad_mensual([], [], meses=2, clock=lambda: date(2026, 2, 15))

    assert all(item.ingresos == Decimal("0") and item.gastos == Decimal("0") for item in resultado)


def test_rentabilidad_mensual_excludes_pautas_paid_in_a_different_month() -> None:
    pautas = [_pauta(fecha_pago=date(2025, 12, 31), valor_pagado=Decimal("100000"))]

    resultado = rentabilidad_mensual(pautas, [], meses=1, clock=lambda: date(2026, 1, 31))

    assert resultado[0].ingresos == Decimal("0")


def test_rentabilidad_mensual_handles_year_boundary() -> None:
    resultado = rentabilidad_mensual([], [], meses=2, clock=lambda: date(2026, 1, 15))

    assert [(item.anio, item.mes) for item in resultado] == [
        (2025, 12),
        (2026, 1),
    ]
