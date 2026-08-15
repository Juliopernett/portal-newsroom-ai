"""Domain service: monthly profitability (ingresos - gastos) over a date range.

Deliberately not a method on `AnalyticsService` — that class is bound to a
fixed `clients`/`pautas`/`solicitudes`/`destinos` snapshot at construction
(see its own docstring), and every existing caller passes those four.
Rentabilidad only needs `pautas` and `gastos`, which have nothing to do
with each other's domains (revenue vs. operating cost) — adding `gastos`
to `AnalyticsService.__init__` would force every unrelated call site to
start wiring a repository it never asked for. Same reasoning that already
keeps `core.services.pauta_service.PautaService` a separate, stateless
service instead of folding into `AnalyticsService`.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from core.analytics.view_models import RentabilidadMensualItem
from core.entities.gasto import Gasto
from core.entities.pauta import Pauta


def meses_atras(anio: int, mes: int, n: int) -> tuple[int, int]:
    """Return the (año, mes) that is `n` calendar months before (año, mes)."""
    total = anio * 12 + (mes - 1) - n
    return total // 12, total % 12 + 1


def rentabilidad_mensual(
    pautas: Sequence[Pauta],
    gastos: Sequence[Gasto],
    *,
    desde: date,
    hasta: date,
) -> list[RentabilidadMensualItem]:
    """Return every calendar month from `desde` to `hasta` (both inclusive), oldest first.

    `desde`/`hasta` are explicit — this function has no notion of "today"
    (Sprint "reportes por rango de fechas", 2026-08-14: the Dashboard's
    default 12-meses window and the report screen's custom range are both
    just callers passing different dates, not two code paths). See
    `app.api.routers.dashboard.get_rentabilidad` for the default-range
    computation.

    `ingresos` groups `Pauta.valor_pagado` by the month of `fecha_pago` —
    the same "dinero ya cobrado" definition the dashboard's "Ingresos
    último mes"/"Pautado este mes" already use (see
    `app.api.static.app.js::calcularIngresosDelMes`), not `fecha_inicio`.
    `gastos` groups `Gasto.valor` by the month of `Gasto.fecha`. Months
    with no ingresos or no gastos still appear, at zero — a report that
    silently skipped an empty month would look like missing data, not a
    quiet month.
    """
    meses_rango: list[tuple[int, int]] = []
    anio, mes = desde.year, desde.month
    while (anio, mes) <= (hasta.year, hasta.month):
        meses_rango.append((anio, mes))
        mes += 1
        if mes == 13:
            mes = 1
            anio += 1

    ingresos_por_mes: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for pauta in pautas:
        clave = (pauta.fecha_pago.year, pauta.fecha_pago.month)
        ingresos_por_mes[clave] += pauta.valor_pagado

    gastos_por_mes: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for gasto in gastos:
        clave = (gasto.fecha.year, gasto.fecha.month)
        gastos_por_mes[clave] += gasto.valor

    resultado = []
    for clave in meses_rango:
        ingresos = ingresos_por_mes[clave]
        gastos_mes = gastos_por_mes[clave]
        resultado.append(
            RentabilidadMensualItem(
                anio=clave[0],
                mes=clave[1],
                ingresos=ingresos,
                gastos=gastos_mes,
                rentabilidad=ingresos - gastos_mes,
            )
        )
    return resultado
