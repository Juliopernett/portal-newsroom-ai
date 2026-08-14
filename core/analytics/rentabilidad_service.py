"""Domain service: monthly profitability (ingresos - gastos).

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
from collections.abc import Callable, Sequence
from datetime import date
from decimal import Decimal

from core.analytics.view_models import RentabilidadMensualItem
from core.clock import now_local
from core.entities.gasto import Gasto
from core.entities.pauta import Pauta


def rentabilidad_mensual(
    pautas: Sequence[Pauta],
    gastos: Sequence[Gasto],
    *,
    meses: int = 12,
    clock: Callable[[], date] = lambda: now_local().date(),
) -> list[RentabilidadMensualItem]:
    """Return the last `meses` calendar months, oldest first, ingresos vs. gastos.

    `ingresos` groups `Pauta.valor_pagado` by the month of `fecha_pago` —
    the same "dinero ya cobrado" definition the dashboard's "Ingresos
    último mes"/"Pautado este mes" already use (see
    `app.api.static.app.js::calcularIngresosDelMes`), not `fecha_inicio`.
    `gastos` groups `Gasto.valor` by the month of `Gasto.fecha`. Months
    with no ingresos or no gastos still appear, at zero — a report that
    silently skipped an empty month would look like missing data, not a
    quiet month.
    """
    hoy = clock()
    meses_rango: list[tuple[int, int]] = []
    anio, mes = hoy.year, hoy.month
    for _ in range(meses):
        meses_rango.append((anio, mes))
        mes -= 1
        if mes == 0:
            mes = 12
            anio -= 1
    meses_rango.reverse()

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
