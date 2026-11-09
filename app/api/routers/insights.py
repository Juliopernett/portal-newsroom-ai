"""Routes for the Centro de Decisión (Sprint 5A).

Every value returned here is read straight from
`core.analytics.DecisionEngineService` — this router fetches the three
repository lists that service needs and serializes exactly what it
computes. It never recomputes a business rule, same convention
`app.api.routers.dashboard` already follows for `AnalyticsService`.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_ai_provider, get_current_user, get_unit_of_work
from app.api.schemas.client import ClientOut
from app.api.schemas.insights import (
    AlertaInteligenteOut,
    AsesorOut,
    SugerenciaOut,
    ClienteCuentaPorCobrarOut,
    ClienteDormidoOut,
    ClienteRiesgoAbandonoOut,
    ClienteScoreSaludOut,
    OportunidadComercialOut,
)
from core.analytics import (
    AnalyticsService,
    DecisionEngineService,
    rango_por_defecto,
    rentabilidad_mensual,
)
from core.clock import now_local
from core.ports.ai_provider import AIProvider
from core.ports.unit_of_work import UnitOfWork
from core.services.asesor_negocio_service import AsesorError, analizar_negocio

router = APIRouter(prefix="/insights", tags=["insights"], dependencies=[Depends(get_current_user)])


def _decision_engine(uow: UnitOfWork) -> DecisionEngineService:
    return DecisionEngineService(
        clients=uow.clients.list_all(),
        pautas=uow.pautas.list_all(),
        solicitudes=uow.publication_requests.list_all(),
        destinos=uow.destinos_publicacion.list_all(),
    )


@router.get("/salud-clientes", response_model=list[ClienteScoreSaludOut])
def get_salud_clientes(
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[ClienteScoreSaludOut]:
    """Return every Client's health score, worst first."""
    engine = _decision_engine(uow)
    return [
        ClienteScoreSaludOut(
            cliente=ClientOut.model_validate(item.cliente),
            score=item.score,
            estrellas=item.estrellas,
            nivel=item.nivel,
        )
        for item in engine.scores_salud()
    ]


@router.get("/centro-alertas", response_model=list[AlertaInteligenteOut])
def get_centro_alertas(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[AlertaInteligenteOut]:
    """Return the prioritized, actionable alert list — severity order."""
    engine = _decision_engine(uow)
    return [
        AlertaInteligenteOut(
            tipo=item.tipo,
            severidad=item.severidad,
            mensaje=item.mensaje,
            cliente=ClientOut.model_validate(item.cliente) if item.cliente is not None else None,
            accion=item.accion,
            dias=item.dias,
        )
        for item in engine.centro_alertas()
    ]


@router.get("/riesgo-abandono", response_model=list[ClienteRiesgoAbandonoOut])
def get_riesgo_abandono(
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[ClienteRiesgoAbandonoOut]:
    """Return Clients with a vigente, unexhausted Pauta who have gone quiet."""
    engine = _decision_engine(uow)
    return [
        ClienteRiesgoAbandonoOut(
            cliente=ClientOut.model_validate(item.cliente),
            dias_sin_actividad=item.dias_sin_actividad,
            publicaciones_restantes=item.publicaciones_restantes,
            fecha_vencimiento=item.fecha_vencimiento,
        )
        for item in engine.clientes_riesgo_abandono()
    ]


@router.get("/cuentas-por-cobrar", response_model=list[ClienteCuentaPorCobrarOut])
def get_cuentas_por_cobrar(
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[ClienteCuentaPorCobrarOut]:
    """Return every Pauta with an unpaid balance, largest debt first."""
    engine = _decision_engine(uow)
    return [
        ClienteCuentaPorCobrarOut(
            cliente=ClientOut.model_validate(item.cliente),
            pauta_id=item.pauta_id,
            saldo_pendiente=item.saldo_pendiente,
            tipo=item.tipo,
            fecha_fin=item.fecha_fin,
        )
        for item in engine.cuentas_por_cobrar()
    ]


@router.get("/dormidos", response_model=list[ClienteDormidoOut])
def get_dormidos(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[ClienteDormidoOut]:
    """Return Clients with no vigente Pauta who have gone quiet for a long time."""
    engine = _decision_engine(uow)
    return [
        ClienteDormidoOut(
            cliente=ClientOut.model_validate(item.cliente),
            dias_sin_actividad=item.dias_sin_actividad,
            ultimo_contrato_tipo=item.ultimo_contrato.tipo,
            ultimo_contrato_fecha_fin=item.ultimo_contrato.fecha_fin,
        )
        for item in engine.clientes_dormidos()
    ]


@router.get("/oportunidades", response_model=list[OportunidadComercialOut])
def get_oportunidades(
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[OportunidadComercialOut]:
    """Return every fine-grained buying-pattern opportunity detected."""
    engine = _decision_engine(uow)
    return [
        OportunidadComercialOut(
            cliente=ClientOut.model_validate(item.cliente),
            tipo=item.tipo,
            mensaje=item.mensaje,
            racha=item.racha,
            tipo_habitual=item.tipo_habitual,
            porcentaje_consumido=item.porcentaje_consumido,
        )
        for item in engine.oportunidades_comerciales()
    ]


def _foto_del_negocio(uow: UnitOfWork) -> dict[str, Any]:
    """Condense the business into a few dozen facts for the advisor (read-only)."""
    hoy = now_local().date()
    clients = uow.clients.list_all()
    pautas = uow.pautas.list_all()
    solicitudes = uow.publication_requests.list_all()
    destinos = uow.destinos_publicacion.list_all()
    otros = uow.otros_ingresos.list_all()
    engine = DecisionEngineService(
        clients=clients, pautas=pautas, solicitudes=solicitudes, destinos=destinos
    )
    analytics = AnalyticsService(
        clients=clients,
        pautas=pautas,
        solicitudes=solicitudes,
        destinos=destinos,
        otros_ingresos=otros,
    )
    desde, hasta = rango_por_defecto(None, None, hoy)
    meses = rentabilidad_mensual(pautas, uow.gastos.list_all(), otros, desde=desde, hasta=hasta)
    reciente = [s for s in solicitudes if (hoy - s.fecha_recepcion.date()).days <= 30]
    canales = Counter(
        d.canal.value
        for d in destinos
        if d.estado.value == "publicado"
        and d.fecha_publicacion is not None
        and (hoy - d.fecha_publicacion.date()).days <= 30
    )
    return {
        "hoy": hoy.isoformat(),
        "resumen": {
            "clientes_activos": analytics.cantidad_clientes_activos(),
            "contratos_vigentes": analytics.cantidad_pautas_vigentes(),
            "contratos_vencidos": analytics.cantidad_pautas_vencidas(),
            "solicitudes_pendientes": analytics.cantidad_publicaciones_pendientes(),
            "publicaciones_este_mes": analytics.cantidad_publicaciones_publicadas_este_mes(),
        },
        "ultimos_12_meses": [
            {
                "mes": f"{m.anio}-{m.mes:02d}",
                "ingresos": m.ingresos,
                "gastos": m.gastos,
                "utilidad": m.rentabilidad,
            }
            for m in meses
        ],
        "solicitudes_ultimos_30_dias": len(reciente),
        "publicaciones_por_canal_ultimos_30_dias": dict(canales),
        "mayores_contratos": [
            {
                "cliente": r.cliente.nombre,
                "valor": r.valor_contratado,
                "restantes": r.publicaciones_restantes,
                "de": r.publicaciones_contratadas,
                "vence": r.fecha_vencimiento,
                "estado": r.estado_comercial.value,
            }
            for r in analytics.ranking_comercial()[:12]
        ],
        "alertas": [
            {"tipo": a.tipo.value, "severidad": a.severidad.value, "mensaje": a.mensaje}
            for a in engine.centro_alertas()[:15]
        ],
        "riesgo_abandono": [
            {"cliente": r.cliente.nombre, "dias_sin_actividad": r.dias_sin_actividad}
            for r in engine.clientes_riesgo_abandono()[:10]
        ],
        "cuentas_por_cobrar": [
            {"cliente": c.cliente.nombre, "saldo": c.saldo_pendiente}
            for c in engine.cuentas_por_cobrar()[:10]
        ],
        "clientes_dormidos": [
            {"cliente": d.cliente.nombre, "dias_sin_actividad": d.dias_sin_actividad}
            for d in engine.clientes_dormidos()[:10]
        ],
        "oportunidades": [
            {"cliente": o.cliente.nombre, "senal": o.mensaje}
            for o in engine.oportunidades_comerciales()[:10]
        ],
    }


@router.post("/asesor", response_model=AsesorOut)
def post_asesor(
    uow: UnitOfWork = Depends(get_unit_of_work),
    ai_provider: AIProvider = Depends(get_ai_provider),
) -> AsesorOut:
    """Ask the AI advisor to read the business numbers and suggest improvements.

    On demand only. Read-only: it never changes data and never contacts a
    client — the owner decides what to do with each suggestion.
    """
    try:
        analisis = analizar_negocio(_foto_del_negocio(uow), ai_provider)
    except AsesorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AsesorOut(
        resumen=analisis.resumen,
        sugerencias=[
            SugerenciaOut(
                titulo=s.titulo,
                detalle=s.detalle,
                prioridad=s.prioridad,
                area=s.area,
                cliente=s.cliente,
            )
            for s in analisis.sugerencias
        ],
    )
