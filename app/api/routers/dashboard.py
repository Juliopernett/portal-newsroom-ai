"""Routes for the Dashboard Comercial (Sprint 4B).

Every value returned here is read straight from `core.analytics.AnalyticsService`
— this router fetches the three repository lists that service needs and
serializes exactly what it computes. It never recomputes a business rule
and never touches `core.entities`/`core.services` beyond what
`AnalyticsService` already exposes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.client import ClientOut
from app.api.schemas.dashboard import DashboardAlertasOut, DashboardResumenOut, RankingComercialOut
from app.api.schemas.publication_request import PublicationRequestOut
from core.analytics import AnalyticsService
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(
    prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)]
)


def _analytics(uow: UnitOfWork) -> AnalyticsService:
    return AnalyticsService(
        clients=uow.clients.list_all(),
        pautas=uow.pautas.list_all(),
        solicitudes=uow.publication_requests.list_all(),
    )


@router.get("/resumen", response_model=DashboardResumenOut)
def get_resumen(uow: UnitOfWork = Depends(get_unit_of_work)) -> DashboardResumenOut:
    """Return the Resumen General cards — Sección 1."""
    analytics = _analytics(uow)
    return DashboardResumenOut(
        clientes_activos=analytics.cantidad_clientes_activos(),
        pautas_activas=analytics.cantidad_pautas_vigentes(),
        pautas_vencidas=analytics.cantidad_pautas_vencidas(),
        solicitudes_pendientes=analytics.cantidad_publicaciones_pendientes(),
        publicaciones_este_mes=analytics.cantidad_publicaciones_publicadas_este_mes(),
        ingreso_contratado_activo=analytics.ingresos_activos(),
        ingreso_historico=analytics.ingresos_historicos(),
        peso_comercial_promedio=analytics.peso_comercial_promedio(),
    )


@router.get("/alertas", response_model=DashboardAlertasOut)
def get_alertas(uow: UnitOfWork = Depends(get_unit_of_work)) -> DashboardAlertasOut:
    """Return the Alertas lists — Sección 2, ordered by category severity."""
    analytics = _analytics(uow)
    return DashboardAlertasOut(
        clientes_cupo_agotado=[
            ClientOut.model_validate(c) for c in analytics.clientes_con_cupo_agotado()
        ],
        clientes_por_vencer=[
            ClientOut.model_validate(c) for c in analytics.clientes_por_vencer(dias=7)
        ],
        clientes_cupo_bajo=[
            ClientOut.model_validate(c)
            for c in analytics.clientes_con_menos_de_n_publicaciones_restantes(minimo=3)
        ],
        solicitudes_antiguas=[
            PublicationRequestOut.model_validate(s)
            for s in analytics.solicitudes_antiguas(horas=4)
        ],
    )


@router.get("/ranking", response_model=list[RankingComercialOut])
def get_ranking(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[RankingComercialOut]:
    """Return the Ranking Comercial — Sección 3, sorted by peso_comercial desc."""
    analytics = _analytics(uow)
    return [
        RankingComercialOut(
            cliente=ClientOut.model_validate(item.cliente),
            valor_contratado=item.valor_contratado,
            peso_comercial=item.peso_comercial,
            publicaciones_restantes=item.publicaciones_restantes,
            fecha_vencimiento=item.fecha_vencimiento,
            vigente=item.vigente,
        )
        for item in analytics.ranking_comercial()
    ]
