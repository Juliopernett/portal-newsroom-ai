"""Routes for the Excel exports (pestaña Reportes).

Plain HTTP downloads (`Content-Disposition: attachment`), not JSON consumed
by the frontend: the file is built here, with real dates and numbers.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, same convention as every other router in this package.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.excel_reportes import Columna, Formato, Hoja, construir_excel
from core.analytics import rango_por_defecto, rentabilidad_mensual
from core.clock import now_local
from core.entities.colores_marca import ColoresMarca
from core.entities.pauta import PautaTipo
from core.ports.unit_of_work import UnitOfWork
from core.services.pauta_service import PautaService

router = APIRouter(prefix="/reportes", tags=["reportes"], dependencies=[Depends(get_current_user)])

_EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_PAUTA_TIPO_LABELS = {
    PautaTipo.INDIVIDUAL: "Individual",
    PautaTipo.MENSUAL: "Mensual",
    PautaTipo.BIMESTRAL: "Bimestral",
    PautaTipo.TRIMESTRAL: "Trimestral",
    PautaTipo.SEMESTRAL: "Semestral",
    PautaTipo.ANUAL: "Anual",
}


def _excel_response(filename: str, hojas: list[Hoja], uow: UnitOfWork) -> Response:
    """Build a downloadable `.xlsx` `Response`, headed with the brand's background colour."""
    colores = uow.colores_marca.get() or ColoresMarca()
    return Response(
        content=construir_excel(hojas, colores.fondo),
        media_type=_EXCEL_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _en_rango(fecha: date, desde: date | None, hasta: date | None) -> bool:
    return (desde is None or fecha >= desde) and (hasta is None or fecha <= hasta)


def _hoja_rentabilidad(uow: UnitOfWork, desde: date, hasta: date) -> Hoja:
    items = rentabilidad_mensual(
        uow.pautas.list_all(),
        uow.gastos.list_all(),
        uow.otros_ingresos.list_all(),
        desde=desde,
        hasta=hasta,
    )
    return Hoja(
        "Rentabilidad",
        [
            Columna("Mes", Formato.MES),
            Columna("Ingresos", Formato.PESOS, totalizar=True),
            Columna("Gastos", Formato.PESOS, totalizar=True),
            Columna("Rentabilidad", Formato.PESOS, totalizar=True),
        ],
        [
            [date(item.anio, item.mes, 1), item.ingresos, item.gastos, item.rentabilidad]
            for item in items
        ],
    )


def _hoja_pautas(uow: UnitOfWork, desde: date | None, hasta: date | None) -> Hoja:
    """Pautas cuyo `fecha_inicio` cae en el rango, ordenadas por `fecha_inicio`."""
    clientes_por_id = {cliente.id: cliente for cliente in uow.clients.list_all()}
    solicitudes = uow.publication_requests.list_all()
    destinos = uow.destinos_publicacion.list_all()
    service = PautaService()

    pautas = [p for p in uow.pautas.list_all() if _en_rango(p.fecha_inicio, desde, hasta)]
    pautas.sort(key=lambda pauta: pauta.fecha_inicio)

    filas: list[list[object]] = []
    for pauta in pautas:
        cliente = clientes_por_id.get(pauta.client_id)
        filas.append(
            [
                cliente.nombre if cliente else "(cliente desconocido)",
                _PAUTA_TIPO_LABELS[pauta.tipo],
                pauta.fecha_inicio,
                pauta.fecha_fin,
                pauta.publicaciones_contratadas,
                service.publicaciones_restantes(pauta, solicitudes, destinos),
                pauta.valor_pagado,
                pauta.fecha_pago,
                "Vigente" if service.esta_vigente(pauta) else "Vencido",
            ]
        )
    return Hoja(
        "Pautas",
        [
            Columna("Cliente"),
            Columna("Tipo"),
            Columna("Fecha inicio", Formato.FECHA),
            Columna("Fecha fin", Formato.FECHA),
            Columna("Publicaciones contratadas", Formato.ENTERO, totalizar=True),
            Columna("Publicaciones restantes", Formato.ENTERO, totalizar=True),
            Columna("Valor pagado", Formato.PESOS, totalizar=True),
            Columna("Fecha pago", Formato.FECHA),
            Columna("Estado"),
        ],
        filas,
    )


def _hoja_gastos(uow: UnitOfWork, desde: date | None, hasta: date | None) -> Hoja:
    """Gastos cuya `fecha` cae en el rango, ordenados por fecha."""
    gastos = [g for g in uow.gastos.list_all() if _en_rango(g.fecha, desde, hasta)]
    gastos.sort(key=lambda gasto: gasto.fecha)
    return Hoja(
        "Gastos",
        [
            Columna("Fecha", Formato.FECHA),
            Columna("Descripción"),
            Columna("Valor", Formato.PESOS, totalizar=True),
        ],
        [[gasto.fecha, gasto.descripcion, gasto.valor] for gasto in gastos],
    )


def _hoja_otros_ingresos(uow: UnitOfWork, desde: date | None, hasta: date | None) -> Hoja:
    """OtroIngreso cuya `fecha_cobro` cae en el rango, ordenados por fecha.

    El contraparte de ingreso de `_hoja_gastos`, para auditar por separado lo
    que ya entra sumado (sin distinguir origen) en la rentabilidad.
    """
    ingresos = [i for i in uow.otros_ingresos.list_all() if _en_rango(i.fecha_cobro, desde, hasta)]
    ingresos.sort(key=lambda ingreso: ingreso.fecha_cobro)
    return Hoja(
        "Otros ingresos",
        [
            Columna("Fecha", Formato.FECHA),
            Columna("Origen"),
            Columna("Valor (COP)", Formato.PESOS, totalizar=True),
            Columna("Valor (USD)", Formato.DOLARES, totalizar=True),
            Columna("Notas"),
        ],
        [[i.fecha_cobro, i.origen, i.monto, i.monto_usd, i.observaciones] for i in ingresos],
    )


def _rango_completo(uow: UnitOfWork, desde: date | None, hasta: date | None) -> tuple[date, date]:
    """Months the full report's rentabilidad covers: without dates, the whole history.

    The other sheets show every record when there are no dates, so a 12-month
    default here would give totals that don't match theirs.
    """
    fechas = [
        *(pauta.fecha_pago for pauta in uow.pautas.list_all()),
        *(gasto.fecha for gasto in uow.gastos.list_all()),
        *(ingreso.fecha_cobro for ingreso in uow.otros_ingresos.list_all()),
    ]
    hoy = now_local().date()
    desde_final = desde or min(fechas, default=hoy)
    hasta_final = hasta or max([hoy, *fechas])
    return desde_final, hasta_final


@router.get("/rentabilidad.xlsx")
def descargar_rentabilidad(
    desde: date | None = None,
    hasta: date | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Rentabilidad mensual en el rango dado — sin fechas, últimos 12 meses.

    Same default-window rule as `GET /dashboard/rentabilidad`, via
    `core.analytics.rango_por_defecto`.
    """
    desde_final, hasta_final = rango_por_defecto(desde, hasta, now_local().date())
    hoja = _hoja_rentabilidad(uow, desde_final, hasta_final)
    return _excel_response("rentabilidad_mensual.xlsx", [hoja], uow)


@router.get("/pautas.xlsx")
def descargar_pautas(
    desde: date | None = None,
    hasta: date | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Pautas por `fecha_inicio` — sin fechas, histórico completo."""
    return _excel_response("pautas.xlsx", [_hoja_pautas(uow, desde, hasta)], uow)


@router.get("/gastos.xlsx")
def descargar_gastos(
    desde: date | None = None,
    hasta: date | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Gastos por `fecha` — sin fechas, histórico completo."""
    return _excel_response("gastos.xlsx", [_hoja_gastos(uow, desde, hasta)], uow)


@router.get("/otros-ingresos.xlsx")
def descargar_otros_ingresos(
    desde: date | None = None,
    hasta: date | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Otros ingresos por `fecha_cobro` — sin fechas, histórico completo."""
    hoja = _hoja_otros_ingresos(uow, desde, hasta)
    return _excel_response("otros_ingresos.xlsx", [hoja], uow)


@router.get("/completo.xlsx")
def descargar_completo(
    desde: date | None = None,
    hasta: date | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> Response:
    """Los cuatro reportes en un solo archivo, una pestaña cada uno."""
    hojas = [
        _hoja_rentabilidad(uow, *_rango_completo(uow, desde, hasta)),
        _hoja_pautas(uow, desde, hasta),
        _hoja_gastos(uow, desde, hasta),
        _hoja_otros_ingresos(uow, desde, hasta),
    ]
    return _excel_response("reporte_completo.xlsx", hojas, uow)
