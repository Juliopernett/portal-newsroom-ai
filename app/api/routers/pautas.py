"""Routes for Pauta.

`GET /pautas/{pauta_id}` is what "consultar el estado de las publicaciones
restantes" (Sprint 3D) actually is — it reuses
`core.services.pauta_service.PautaService`, already built and tested in
Sprint 3B, without any new domain logic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_unit_of_work
from app.api.schemas.pauta import PautaCreate, PautaOut
from core.entities.pauta import Pauta
from core.ports.unit_of_work import UnitOfWork
from core.services.pauta_service import PautaService

router = APIRouter(prefix="/pautas", tags=["pautas"])


def _to_out(pauta: Pauta, uow: UnitOfWork) -> PautaOut:
    solicitudes = uow.publication_requests.list_by_pauta_id(pauta.id)
    service = PautaService()
    return PautaOut(
        id=pauta.id,
        client_id=pauta.client_id,
        fecha_inicio=pauta.fecha_inicio,
        fecha_fin=pauta.fecha_fin,
        publicaciones_contratadas=pauta.publicaciones_contratadas,
        valor_pagado=pauta.valor_pagado,
        fecha_pago=pauta.fecha_pago,
        observaciones=pauta.observaciones,
        publicaciones_consumidas=service.publicaciones_consumidas(pauta, solicitudes),
        publicaciones_restantes=service.publicaciones_restantes(pauta, solicitudes),
        vigente=service.esta_vigente(pauta),
        vencida=service.esta_vencida(pauta),
        cuota_agotada=service.cuota_agotada(pauta, solicitudes),
        peso_comercial=pauta.peso_comercial,
    )


@router.post("", response_model=PautaOut, status_code=201)
def create_pauta(payload: PautaCreate, uow: UnitOfWork = Depends(get_unit_of_work)) -> PautaOut:
    """Register a new Pauta for an existing Client."""
    pauta = Pauta(**payload.model_dump())
    uow.pautas.save(pauta)
    uow.commit()
    return _to_out(pauta, uow)


@router.get("/{pauta_id}", response_model=PautaOut)
def get_pauta(pauta_id: str, uow: UnitOfWork = Depends(get_unit_of_work)) -> PautaOut:
    """Return a Pauta with its computed quota status."""
    pauta = uow.pautas.get_by_id(pauta_id)
    if pauta is None:
        raise HTTPException(status_code=404, detail="Pauta not found")
    return _to_out(pauta, uow)


@router.get("", response_model=list[PautaOut])
def list_pautas(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[PautaOut]:
    """Return every Pauta with its computed quota status — the admin screen's data."""
    return [_to_out(pauta, uow) for pauta in uow.pautas.list_all()]
