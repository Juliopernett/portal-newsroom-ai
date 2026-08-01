"""Routes for PublicationRequest.

`POST /{request_id}/publish` exposes the existing
`core.services.publication_request_service.mark_as_published` operation.
`POST /{request_id}/link-pauta` (Sprint 3E) closes the gap the UX review
(docs/ux/sprint-3d5-ux-review.md) flagged as the most important one: a
request received without a Pauta had no way to be completed from the
interface — it exposes `link_pauta`, itself just `dataclasses.replace`
on an existing field, no new domain rule.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.publication_request import (
    PublicationRequestCreate,
    PublicationRequestLinkPauta,
    PublicationRequestOut,
)
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.ports.unit_of_work import UnitOfWork
from core.services.publication_request_service import link_pauta, mark_as_published

router = APIRouter(
    prefix="/publication-requests",
    tags=["publication-requests"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=PublicationRequestOut, status_code=201)
def create_publication_request(
    payload: PublicationRequestCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> PublicationRequest:
    """Register a new commercial publication request, received as RECIBIDA."""
    solicitud = PublicationRequest(**payload.model_dump())
    uow.publication_requests.save(solicitud)
    uow.commit()
    return solicitud


@router.get("", response_model=list[PublicationRequestOut])
def list_publication_requests(
    estado: PublicationRequestStatus | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[PublicationRequest]:
    """Return requests, optionally filtered to a single `estado` (e.g. RECIBIDA)."""
    return uow.publication_requests.list_all(estado=estado)


@router.post("/{request_id}/publish", response_model=PublicationRequestOut)
def publish_publication_request(
    request_id: str, uow: UnitOfWork = Depends(get_unit_of_work)
) -> PublicationRequest:
    """Mark an existing PublicationRequest as PUBLICADA."""
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    publicada = mark_as_published(solicitud)
    uow.publication_requests.save(publicada)
    uow.commit()
    return publicada


@router.post("/{request_id}/link-pauta", response_model=PublicationRequestOut)
def link_pauta_to_publication_request(
    request_id: str,
    payload: PublicationRequestLinkPauta,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> PublicationRequest:
    """Link an existing PublicationRequest to a Pauta, without changing its estado."""
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    vinculada = link_pauta(solicitud, payload.pauta_id)
    uow.publication_requests.save(vinculada)
    uow.commit()
    return vinculada
