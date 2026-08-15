"""Routes for CSV exports (pestaña Reportes, 2026-08-15).

Plain HTTP downloads (`Content-Disposition: attachment`), not JSON consumed
by the frontend and turned into a client-side Blob — a real file download
is a normal browser navigation (works with cookie-based auth exactly like
any other page, no `fetch`/Blob/anchor-click plumbing needed) and doesn't
depend on the browser honoring a script-triggered download, which is the
class of bug the previous client-side CSV export was exposed to.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, same convention as every other router in this package.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.dependencies import get_current_user, get_unit_of_work
from core.analytics import rango_por_defecto, rentabilidad_mensual
from core.clock import now_local
from core.entities.pauta import PautaTipo
from core.ports.unit_of_work import UnitOfWork
from core.services.pauta_service import PautaService

router = APIRouter(prefix="/reportes", tags=["reportes"], dependencies=[Depends(get_current_user)])

_PAUTA_TIPO_LABELS = {
    PautaTipo.INDIVIDUAL: "Individual",
    PautaTipo.MENSUAL: "Mensual",
    PautaTipo.BIMESTRAL: "Bimestral",
    PautaTipo.TRIMESTRAL: "Trimestral",
    PautaTipo.SEMESTRAL: "Semestral",
    PautaTipo.ANUAL: "Anual",
}


def _csv_response(filename: str, encabezados: list[str], filas: list[list[object]]) -> Response:
    """Build a downloadable CSV `Response` — UTF-8 BOM so Excel opens accents/ñ correctly."""
    buffer = io.StringIO()
    buffer.write("﻿")
    writer = csv.writer(buffer)
    writer.writerow(encabezados)
    writer.writerows(filas)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/rentabilidad.csv")
def descargar_rentabilidad_csv(
    desde: date | None = None,
    hasta: date | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Rentabilidad mensual en el rango dado — sin fechas, últimos 12 meses.

    Same default-window rule as `GET /dashboard/rentabilidad`, via
    `core.analytics.rango_por_defecto`.
    """
    desde_final, hasta_final = rango_por_defecto(desde, hasta, now_local().date())
    items = rentabilidad_mensual(
        uow.pautas.list_all(), uow.gastos.list_all(), desde=desde_final, hasta=hasta_final
    )
    filas = [[f"{item.anio}-{item.mes:02d}", item.ingresos, item.gastos, item.rentabilidad] for item in items]
    return _csv_response(
        "rentabilidad_mensual.csv", ["Mes", "Ingresos", "Gastos", "Rentabilidad"], filas
    )


@router.get("/pautas.csv")
def descargar_pautas_csv(
    desde: date | None = None,
    hasta: date | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Pautas cuyo `fecha_inicio` cae en el rango dado — sin fechas, histórico completo.

    Ordenado por `fecha_inicio`. `desde`/`hasta` filtran sobre `fecha_inicio`,
    la misma convención que el filtro por rango que existía en la pestaña
    Contratos antes de moverse aquí.
    """
    clientes_por_id = {cliente.id: cliente for cliente in uow.clients.list_all()}
    solicitudes = uow.publication_requests.list_all()
    destinos = uow.destinos_publicacion.list_all()
    service = PautaService()

    pautas = [
        pauta
        for pauta in uow.pautas.list_all()
        if (desde is None or pauta.fecha_inicio >= desde)
        and (hasta is None or pauta.fecha_inicio <= hasta)
    ]
    pautas.sort(key=lambda pauta: pauta.fecha_inicio)

    filas = []
    for pauta in pautas:
        cliente = clientes_por_id.get(pauta.client_id)
        filas.append(
            [
                cliente.nombre if cliente else "(cliente desconocido)",
                _PAUTA_TIPO_LABELS[pauta.tipo],
                pauta.fecha_inicio.isoformat(),
                pauta.fecha_fin.isoformat(),
                pauta.publicaciones_contratadas,
                service.publicaciones_restantes(pauta, solicitudes, destinos),
                pauta.valor_pagado,
                pauta.fecha_pago.isoformat(),
                "Vigente" if service.esta_vigente(pauta) else "Vencido",
            ]
        )
    return _csv_response(
        "pautas.csv",
        [
            "Cliente",
            "Tipo",
            "Fecha inicio",
            "Fecha fin",
            "Publicaciones contratadas",
            "Publicaciones restantes",
            "Valor pagado",
            "Fecha pago",
            "Estado",
        ],
        filas,
    )


@router.get("/gastos.csv")
def descargar_gastos_csv(
    desde: date | None = None,
    hasta: date | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Gastos cuya `fecha` cae en el rango dado, ordenados por fecha — sin fechas, histórico completo."""
    gastos = [
        gasto
        for gasto in uow.gastos.list_all()
        if (desde is None or gasto.fecha >= desde) and (hasta is None or gasto.fecha <= hasta)
    ]
    gastos.sort(key=lambda gasto: gasto.fecha)
    filas = [[gasto.fecha.isoformat(), gasto.descripcion, gasto.valor] for gasto in gastos]
    return _csv_response("gastos.csv", ["Fecha", "Descripción", "Valor"], filas)
