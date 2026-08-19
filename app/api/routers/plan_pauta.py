"""Routes for PlanPauta — the Configuración pricing catalog.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, same discipline `app.api.routers.gastos` uses.
"""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.plan_pauta import PlanPautaCreate, PlanPautaOut
from core.entities.plan_pauta import PlanPauta
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(
    prefix="/planes-pauta", tags=["planes-pauta"], dependencies=[Depends(get_current_user)]
)


@router.post("", response_model=PlanPautaOut, status_code=201)
def create_plan_pauta(
    payload: PlanPautaCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> PlanPauta:
    """Register a new pricing plan in the Pauta catalog."""
    plan = PlanPauta(**payload.model_dump())
    uow.planes_pauta.save(plan)
    uow.commit()
    return plan


@router.get("", response_model=list[PlanPautaOut])
def list_planes_pauta(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[PlanPauta]:
    """Return every configured plan, ordered for display — the Configuración screen
    and the Plan shortcut in PautaForm."""
    return uow.planes_pauta.list_all()


@router.put("/{plan_id}", response_model=PlanPautaOut)
def update_plan_pauta(
    plan_id: str, payload: PlanPautaCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> PlanPauta:
    """Replace an existing plan's editable fields.

    Same PUT-semantics discipline `app.api.routers.gastos.update_gasto`
    already uses: `PlanPauta` is immutable (`frozen=True`), so this builds
    a new instance via `dataclasses.replace`, which re-runs `__post_init__`
    validation. `id` and `fecha_registro` are preserved.
    """
    existing = uow.planes_pauta.get_by_id(plan_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="PlanPauta not found")
    updated = replace(existing, **payload.model_dump())
    uow.planes_pauta.save(updated)
    uow.commit()
    return updated


@router.delete("/{plan_id}", status_code=204)
def delete_plan_pauta(plan_id: str, uow: UnitOfWork = Depends(get_unit_of_work)) -> None:
    """Remove a plan from the catalog — it stops appearing in PautaForm's shortcut."""
    if uow.planes_pauta.get_by_id(plan_id) is None:
        raise HTTPException(status_code=404, detail="PlanPauta not found")
    uow.planes_pauta.delete(plan_id)
    uow.commit()
