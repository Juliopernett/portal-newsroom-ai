"""Unit tests for the Pauta entity."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from core.entities.pauta import Pauta, PautaTipo


def _build(**overrides: object) -> Pauta:
    defaults: dict[str, object] = {
        "client_id": "client-1",
        "fecha_inicio": date(2026, 7, 30),
        "fecha_fin": date(2026, 8, 30),
        "publicaciones_contratadas": 10,
        "valor_pagado": Decimal("500000"),
        "fecha_pago": date(2026, 7, 30),
    }
    defaults.update(overrides)
    return Pauta(**defaults)


def test_create_pauta_assigns_defaults() -> None:
    pauta = _build()

    assert pauta.id
    assert pauta.observaciones is None


def test_create_pauta_accepts_explicit_values() -> None:
    pauta = _build(id="pauta-1", observaciones="Pago en efectivo")

    assert pauta.id == "pauta-1"
    assert pauta.observaciones == "Pago en efectivo"


def test_create_pauta_rejects_empty_client_id() -> None:
    with pytest.raises(ValueError, match="client_id"):
        _build(client_id="")


@pytest.mark.parametrize(
    "fecha_inicio,fecha_fin",
    [
        (date(2026, 8, 30), date(2026, 8, 30)),  # same day, not a valid range
        (date(2026, 8, 30), date(2026, 7, 30)),  # end before start
    ],
)
def test_create_pauta_rejects_fecha_fin_not_after_fecha_inicio(
    fecha_inicio: date, fecha_fin: date
) -> None:
    with pytest.raises(ValueError, match="fecha_fin"):
        _build(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)


@pytest.mark.parametrize("publicaciones_contratadas", [0, -1])
def test_create_pauta_rejects_non_positive_publicaciones_contratadas(
    publicaciones_contratadas: int,
) -> None:
    with pytest.raises(ValueError, match="publicaciones_contratadas"):
        _build(publicaciones_contratadas=publicaciones_contratadas)


def test_create_pauta_rejects_negative_valor_pagado() -> None:
    with pytest.raises(ValueError, match="valor_pagado"):
        _build(valor_pagado=Decimal("-1"))


def test_pauta_is_immutable() -> None:
    pauta = _build()

    with pytest.raises(AttributeError):
        pauta.publicaciones_contratadas = 20  # type: ignore[misc]


def test_peso_comercial_divides_valor_pagado_by_publicaciones_contratadas() -> None:
    pauta = _build(valor_pagado=Decimal("500000"), publicaciones_contratadas=10)

    assert pauta.peso_comercial == Decimal("50000.00")


def test_peso_comercial_rounds_to_two_decimals_half_up() -> None:
    # 1 / 8 = 0.125 exactamente — ROUND_HALF_EVEN daría 0.12 (2 es par),
    # ROUND_HALF_UP (el que usa peso_comercial) da 0.13.
    pauta = _build(valor_pagado=Decimal("1"), publicaciones_contratadas=8)

    assert pauta.peso_comercial == Decimal("0.13")


def test_peso_comercial_is_zero_when_valor_pagado_is_zero() -> None:
    pauta = _build(valor_pagado=Decimal("0"), publicaciones_contratadas=10)

    assert pauta.peso_comercial == Decimal("0.00")


def _con_duracion(dias: int) -> Pauta:
    inicio = date(2026, 1, 1)
    return _build(fecha_inicio=inicio, fecha_fin=inicio + timedelta(days=dias))


@pytest.mark.parametrize(
    "dias,esperado",
    [
        (1, PautaTipo.INDIVIDUAL),
        (14, PautaTipo.INDIVIDUAL),
        (15, PautaTipo.MENSUAL),
        (31, PautaTipo.MENSUAL),
        (45, PautaTipo.MENSUAL),
        (46, PautaTipo.TRIMESTRAL),
        (90, PautaTipo.TRIMESTRAL),
        (135, PautaTipo.TRIMESTRAL),
        (136, PautaTipo.SEMESTRAL),
        (181, PautaTipo.SEMESTRAL),
        (270, PautaTipo.SEMESTRAL),
        (271, PautaTipo.ANUAL),
        (365, PautaTipo.ANUAL),
    ],
)
def test_tipo_infers_the_commercial_product_from_duration(dias: int, esperado: PautaTipo) -> None:
    assert _con_duracion(dias).tipo == esperado
