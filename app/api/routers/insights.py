"""Routes for the Centro de Decisión (Sprint 5A).

Every value returned here is read straight from
`core.analytics.DecisionEngineService` — this router fetches the three
repository lists that service needs and serializes exactly what it
computes. It never recomputes a business rule, same convention
`app.api.routers.dashboard` already follows for `AnalyticsService`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.client import ClientOut
from app.api.schemas.insights import (
    AlertaInteligenteOut,
    ClienteDormidoOut,
    ClienteRiesgoAbandonoOut,
    ClienteScoreSaludOut,
    OportunidadComercialOut,
)
from core.analytics import DecisionEngineService
from core.ports.unit_of_work import UnitOfWork

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
