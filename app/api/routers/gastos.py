"""Routes for Gasto.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it.
"""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.gasto import GastoCreate, GastoOut
from core.entities.gasto import Gasto
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(prefix="/gastos", tags=["gastos"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=GastoOut, status_code=201)
def create_gasto(payload: GastoCreate, uow: UnitOfWork = Depends(get_unit_of_work)) -> Gasto:
    """Register a new operating expense."""
    gasto = Gasto(**payload.model_dump())
    uow.gastos.save(gasto)
    uow.commit()
    return gasto


@router.get("", response_model=list[GastoOut])
def list_gastos(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[Gasto]:
    """Return every registered expense — the registro screen's data."""
    return uow.gastos.list_all()


@router.put("/{gasto_id}", response_model=GastoOut)
def update_gasto(
    gasto_id: str, payload: GastoCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> Gasto:
    """Replace an existing Gasto's editable fields (descripcion, valor, fecha).

    Same PUT-semantics discipline `app.api.routers.clients.update_client`
    already uses for `Client`: `Gasto` is immutable (`frozen=True`), so
    this builds a new instance via `dataclasses.replace`, which re-runs
    `__post_init__` validation. `id` and `fecha_registro` are preserved.
    """
    existing = uow.gastos.get_by_id(gasto_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Gasto not found")
    updated = replace(existing, **payload.model_dump())
    uow.gastos.save(updated)
    uow.commit()
    return updated


@router.delete("/{gasto_id}", status_code=204)
def delete_gasto(gasto_id: str, uow: UnitOfWork = Depends(get_unit_of_work)) -> None:
    """Delete a Gasto — corrects a duplicate or a mistaken entry."""
    if uow.gastos.get_by_id(gasto_id) is None:
        raise HTTPException(status_code=404, detail="Gasto not found")
    uow.gastos.delete(gasto_id)
    uow.commit()
