"""Routes for OtroIngreso.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it.
"""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.otro_ingreso import OtroIngresoCreate, OtroIngresoOut
from core.entities.otro_ingreso import OtroIngreso
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(
    prefix="/otros-ingresos", tags=["otros-ingresos"], dependencies=[Depends(get_current_user)]
)


@router.post("", response_model=OtroIngresoOut, status_code=201)
def create_otro_ingreso(
    payload: OtroIngresoCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> OtroIngreso:
    """Register income received outside any Pauta (e.g. Facebook, AdSense)."""
    ingreso = OtroIngreso(**payload.model_dump())
    uow.otros_ingresos.save(ingreso)
    uow.commit()
    return ingreso


@router.get("", response_model=list[OtroIngresoOut])
def list_otros_ingresos(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[OtroIngreso]:
    """Return every registered OtroIngreso — the registro screen's data."""
    return uow.otros_ingresos.list_all()


@router.put("/{ingreso_id}", response_model=OtroIngresoOut)
def update_otro_ingreso(
    ingreso_id: str, payload: OtroIngresoCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> OtroIngreso:
    """Replace an existing OtroIngreso's editable fields.

    Same PUT-semantics discipline `app.api.routers.gastos.update_gasto`
    already uses: `OtroIngreso` is immutable (`frozen=True`), so this
    builds a new instance via `dataclasses.replace`, which re-runs
    `__post_init__` validation. `id` and `fecha_registro` are preserved.
    """
    existing = uow.otros_ingresos.get_by_id(ingreso_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="OtroIngreso not found")
    updated = replace(existing, **payload.model_dump())
    uow.otros_ingresos.save(updated)
    uow.commit()
    return updated


@router.delete("/{ingreso_id}", status_code=204)
def delete_otro_ingreso(ingreso_id: str, uow: UnitOfWork = Depends(get_unit_of_work)) -> None:
    """Delete an OtroIngreso — corrects a duplicate or a mistaken entry."""
    if uow.otros_ingresos.get_by_id(ingreso_id) is None:
        raise HTTPException(status_code=404, detail="OtroIngreso not found")
    uow.otros_ingresos.delete(ingreso_id)
    uow.commit()
