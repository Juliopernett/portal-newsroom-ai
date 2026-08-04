"""Routes for Client.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it.
"""

from __future__ import annotations

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.client import ClientCreate, ClientOut
from core.entities.client import Client
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(prefix="/clients", tags=["clients"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=ClientOut, status_code=201)
def create_client(payload: ClientCreate, uow: UnitOfWork = Depends(get_unit_of_work)) -> Client:
    """Register a new commercial client."""
    client = Client(**payload.model_dump())
    uow.clients.save(client)
    uow.commit()
    return client


@router.get("", response_model=list[ClientOut])
def list_clients(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[Client]:
    """Return every registered client."""
    return uow.clients.list_all()


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: str, payload: ClientCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> Client:
    """Replace an existing Client's editable fields (nombre, tipo, telefono, ...).

    `Client` is immutable (`frozen=True`) — this builds a new instance via
    `dataclasses.replace`, which re-runs `__post_init__` validation, the
    same discipline `core.services.publication_request_service` already
    uses for `PublicationRequest`. `id` is preserved; every other field
    is replaced wholesale (PUT semantics — the payload is the new source
    of truth for those fields, not a partial patch).
    """
    existing = uow.clients.get_by_id(client_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Client not found")
    updated = replace(existing, **payload.model_dump())
    uow.clients.save(updated)
    uow.commit()
    return updated
