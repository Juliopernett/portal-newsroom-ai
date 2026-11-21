"""Route for the Deudores section: who owes money, how much and since when.

Read-only and computed on every request from the contracts (`Pauta`) — the
balance itself is still edited where it always was (the Pauta form).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.client import ClientOut
from app.api.schemas.deudores import DeudoresOut, DeudorOut, SaldoPautaOut
from core.clock import now_local
from core.ports.unit_of_work import UnitOfWork
from core.services.deudores_service import agrupar_deudores

router = APIRouter(prefix="/deudores", tags=["deudores"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=DeudoresOut)
def listar_deudores(uow: UnitOfWork = Depends(get_unit_of_work)) -> DeudoresOut:
    """Clients with an unpaid balance, the biggest debt first, with the total to collect."""
    resumen = agrupar_deudores(uow.clients.list_all(), uow.pautas.list_all(), now_local().date())
    return DeudoresOut(
        total_por_cobrar=resumen.total_por_cobrar,
        cantidad=len(resumen.deudores),
        deudores=[
            DeudorOut(
                cliente=ClientOut.model_validate(d.cliente),
                total_pendiente=d.total_pendiente,
                dias_mas_antiguo=d.dias_mas_antiguo,
                saldos=[
                    SaldoPautaOut(
                        pauta_id=s.pauta_id,
                        tipo=s.tipo,
                        saldo_pendiente=s.saldo_pendiente,
                        fecha_pago=s.fecha_pago,
                        fecha_fin=s.fecha_fin,
                        dias_desde_pago=s.dias_desde_pago,
                        vencida=s.vencida,
                    )
                    for s in d.saldos
                ],
            )
            for d in resumen.deudores
        ],
    )
