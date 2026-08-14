"""Unit tests for the Gasto entity."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from core.entities.gasto import Gasto


def _build(**overrides: object) -> Gasto:
    defaults: dict[str, object] = {
        "descripcion": "PAGO MENSUAL ANTONIO",
        "valor": Decimal("350000"),
        "fecha": date(2026, 1, 31),
    }
    defaults.update(overrides)
    return Gasto(**defaults)


def test_create_gasto_assigns_defaults() -> None:
    gasto = _build()

    assert gasto.id
    assert gasto.fecha_registro is not None


def test_create_gasto_accepts_explicit_values() -> None:
    gasto = _build(id="gasto-1")

    assert gasto.id == "gasto-1"


def test_create_gasto_rejects_empty_descripcion() -> None:
    with pytest.raises(ValueError, match="descripcion"):
        _build(descripcion="")


def test_create_gasto_rejects_negative_valor() -> None:
    with pytest.raises(ValueError, match="valor"):
        _build(valor=Decimal("-1"))


def test_create_gasto_accepts_zero_valor() -> None:
    gasto = _build(valor=Decimal("0"))

    assert gasto.valor == Decimal("0")
