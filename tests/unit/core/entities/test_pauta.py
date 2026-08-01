"""Unit tests for the Pauta entity."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from core.entities.pauta import Pauta


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
