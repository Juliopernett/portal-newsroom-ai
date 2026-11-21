"""Debtors: the clients who still owe money on a Pauta, grouped by client.

Pure logic over the data the system already keeps — `Pauta.saldo_pendiente` is
"what the client has not paid yet" (see `core.entities.pauta`). Nothing is
stored here: the view is always computed, so it can never drift from the
contracts. A client can owe on several Pautas; the section shows one row per
client with the total and how long the oldest debt has been open.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from core.entities.client import Client
from core.entities.pauta import Pauta, PautaTipo


@dataclass(frozen=True, slots=True)
class SaldoPauta:
    """What is still owed on one Pauta."""

    pauta_id: str
    tipo: PautaTipo
    saldo_pendiente: Decimal
    fecha_pago: date
    fecha_fin: date
    dias_desde_pago: int  # how long ago the client made the (partial) payment
    vencida: bool  # the plan's end date has already passed


@dataclass(frozen=True, slots=True)
class Deudor:
    """A client with at least one Pauta that has an unpaid balance."""

    cliente: Client
    total_pendiente: Decimal
    saldos: tuple[SaldoPauta, ...]
    dias_mas_antiguo: int


@dataclass(frozen=True, slots=True)
class ResumenDeudores:
    total_por_cobrar: Decimal
    deudores: tuple[Deudor, ...]


def agrupar_deudores(clientes: list[Client], pautas: list[Pauta], hoy: date) -> ResumenDeudores:
    """Group every Pauta with a balance by client, biggest debtor first.

    Pautas whose client no longer exists are ignored (nobody to charge).
    Within a client, the oldest payment goes first.
    """
    por_id = {c.id: c for c in clientes}
    saldos: dict[str, list[SaldoPauta]] = {}
    for p in pautas:
        if p.saldo_pendiente <= 0 or p.client_id not in por_id:
            continue
        saldos.setdefault(p.client_id, []).append(
            SaldoPauta(
                pauta_id=p.id,
                tipo=p.tipo,
                saldo_pendiente=p.saldo_pendiente,
                fecha_pago=p.fecha_pago,
                fecha_fin=p.fecha_fin,
                dias_desde_pago=max(0, (hoy - p.fecha_pago).days),
                vencida=p.fecha_fin < hoy,
            )
        )
    deudores = []
    for client_id, lista in saldos.items():
        lista.sort(key=lambda s: s.fecha_pago)
        deudores.append(
            Deudor(
                cliente=por_id[client_id],
                total_pendiente=sum((s.saldo_pendiente for s in lista), Decimal("0")),
                saldos=tuple(lista),
                dias_mas_antiguo=max(s.dias_desde_pago for s in lista),
            )
        )
    deudores.sort(key=lambda d: (-d.total_pendiente, d.cliente.nombre.lower()))
    return ResumenDeudores(
        total_por_cobrar=sum((d.total_pendiente for d in deudores), Decimal("0")),
        deudores=tuple(deudores),
    )
