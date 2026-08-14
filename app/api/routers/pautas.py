"""Routes for Pauta.

`GET /pautas/{pauta_id}` is what "consultar el estado de las publicaciones
restantes" (Sprint 3D) actually is — it reuses
`core.services.pauta_service.PautaService`, already built and tested in
Sprint 3B, without any new domain logic.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it.
"""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.pauta import PautaCreate, PautaOut
from core.entities.pauta import Pauta
from core.ports.unit_of_work import UnitOfWork
from core.services.pauta_service import PautaService

router = APIRouter(prefix="/pautas", tags=["pautas"], dependencies=[Depends(get_current_user)])


def _to_out(pauta: Pauta, uow: UnitOfWork) -> PautaOut:
    solicitudes = uow.publication_requests.list_by_pauta_id(pauta.id)
    # Sprint 4A, Increment 4: destinos scoped per-solicitud, not
    # uow.destinos_publicacion.list_all() — this runs once per Pauta from
    # list_pautas' loop, and fetching every destino in the system on each
    # iteration would be far more wasteful than these targeted queries.
    destinos = [
        destino
        for solicitud in solicitudes
        for destino in uow.destinos_publicacion.list_by_publication_request_id(solicitud.id)
    ]
    service = PautaService()
    return PautaOut(
        id=pauta.id,
        client_id=pauta.client_id,
        fecha_inicio=pauta.fecha_inicio,
        fecha_fin=pauta.fecha_fin,
        publicaciones_contratadas=pauta.publicaciones_contratadas,
        valor_pagado=pauta.valor_pagado,
        fecha_pago=pauta.fecha_pago,
        fecha_registro=pauta.fecha_registro,
        observaciones=pauta.observaciones,
        publicaciones_consumidas=service.publicaciones_consumidas(pauta, solicitudes, destinos),
        publicaciones_restantes=service.publicaciones_restantes(pauta, solicitudes, destinos),
        vigente=service.esta_vigente(pauta),
        vencida=service.esta_vencida(pauta),
        cuota_agotada=service.cuota_agotada(pauta, solicitudes, destinos),
        peso_comercial=pauta.peso_comercial,
        tipo=pauta.tipo,
    )


@router.post("", response_model=PautaOut, status_code=201)
def create_pauta(payload: PautaCreate, uow: UnitOfWork = Depends(get_unit_of_work)) -> PautaOut:
    """Register a new Pauta for an existing Client."""
    pauta = Pauta(**payload.model_dump())
    uow.pautas.save(pauta)
    uow.commit()
    return _to_out(pauta, uow)


@router.put("/{pauta_id}", response_model=PautaOut)
def update_pauta(
    pauta_id: str, payload: PautaCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> PautaOut:
    """Replace an existing Pauta's editable fields (fecha_inicio, fecha_fin, ...).

    Same PUT-semantics discipline `app.api.routers.clients.update_client`
    already uses for `Client`: `Pauta` is immutable (`frozen=True`), so
    this builds a new instance via `dataclasses.replace`, which re-runs
    `__post_init__` validation. Added 2026-08-14 after a real data-entry
    mistake (a Pauta saved with the wrong fecha_fin) had no way to be
    corrected short of editing the database directly. `id` and
    `fecha_registro` (audit timestamp, never meant to be edited — see
    `Pauta`'s own docstring) are preserved; every other field is replaced
    wholesale from the payload, `client_id` included — the same wholesale
    replacement `Client` already allows.
    """
    existing = uow.pautas.get_by_id(pauta_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Pauta not found")
    updated = replace(existing, **payload.model_dump())
    uow.pautas.save(updated)
    uow.commit()
    return _to_out(updated, uow)


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
