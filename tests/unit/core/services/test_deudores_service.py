"""Unit tests for core.services.deudores_service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.entities.client import Client, ClientType
from core.entities.pauta import Pauta
from core.services.deudores_service import agrupar_deudores

HOY = date(2026, 11, 20)


def _cliente(nombre: str) -> Client:
    return Client(nombre=nombre, tipo=ClientType.ARTISTA, telefono="+573001112233")


def _pauta(cliente: Client, saldo: str, *, pago: date, fin: date | None = None) -> Pauta:
    return Pauta(
        client_id=cliente.id,
        fecha_inicio=date(2026, 10, 1),
        fecha_fin=fin or date(2026, 12, 31),
        publicaciones_contratadas=10,
        valor_pagado=Decimal("500000"),
        fecha_pago=pago,
        saldo_pendiente=Decimal(saldo),
    )


def test_groups_by_client_sums_the_total_and_orders_biggest_first() -> None:
    ana, beto = _cliente("Ana"), _cliente("Beto")
    pautas = [
        _pauta(ana, "100000", pago=date(2026, 11, 10)),
        _pauta(beto, "900000", pago=date(2026, 11, 15)),
        _pauta(ana, "300000", pago=date(2026, 10, 1)),
    ]
    resumen = agrupar_deudores([ana, beto], pautas, HOY)

    assert [d.cliente.nombre for d in resumen.deudores] == ["Beto", "Ana"]
    assert resumen.deudores[1].total_pendiente == Decimal("400000")
    assert resumen.total_por_cobrar == Decimal("1300000")


def test_age_is_counted_from_the_oldest_payment_and_oldest_comes_first() -> None:
    ana = _cliente("Ana")
    pautas = [
        _pauta(ana, "100000", pago=date(2026, 11, 10)),
        _pauta(ana, "300000", pago=date(2026, 10, 1)),
    ]
    deudor = agrupar_deudores([ana], pautas, HOY).deudores[0]

    assert deudor.dias_mas_antiguo == 50
    assert [s.dias_desde_pago for s in deudor.saldos] == [50, 10]


def test_flags_an_expired_plan_and_never_gives_negative_days() -> None:
    ana = _cliente("Ana")
    vencida = _pauta(ana, "100000", pago=date(2026, 11, 25), fin=date(2026, 11, 19))
    saldo = agrupar_deudores([ana], [vencida], HOY).deudores[0].saldos[0]

    assert saldo.vencida is True
    assert saldo.dias_desde_pago == 0  # a payment dated in the future is never "negative"


def test_ignores_paid_up_pautas_and_pautas_of_unknown_clients() -> None:
    ana, fantasma = _cliente("Ana"), _cliente("Borrado")
    pautas = [
        _pauta(ana, "0", pago=date(2026, 11, 1)),
        _pauta(fantasma, "500000", pago=date(2026, 11, 1)),
    ]
    resumen = agrupar_deudores([ana], pautas, HOY)

    assert resumen.deudores == ()
    assert resumen.total_por_cobrar == Decimal("0")
