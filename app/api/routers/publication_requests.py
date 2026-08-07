"""Routes for PublicationRequest.

`POST /{request_id}/publish` (reworked Sprint 4A, Increment 4) is the
pre-multi-destino "Publicar" flow, kept working unchanged from the
operator's point of view: it accepts the request (`estado` → `ACEPTADA`,
same `pauta_id`-required invariant `PUBLICADA` used to enforce) and
creates/marks a compatibility WordPress destino as `PUBLICADO`. See
`publish_publication_request`'s own docstring.

`POST /{request_id}/link-pauta` (Sprint 3E) closes the gap the UX review
(docs/ux/sprint-3d5-ux-review.md) flagged as the most important one: a
request received without a Pauta had no way to be completed from the
interface — it exposes `link_pauta`, itself just `dataclasses.replace`
on an existing field, no new domain rule.
`PATCH /{request_id}` (Sprint UX 3.1; `titulo` added Sprint 4A Increment 2)
exposes `edit_solicitud` — lets an editor fix a typo, set/correct the
titulo, or toggle prioridad_manual on a still-RECIBIDA request without
recreating it.

`/{request_id}/destinos` (Sprint 4A, Increment 3 — see
docs/adr/ADR-006-multichannel-publication.md) exposes `DestinoPublicacion`
CRUD scoped to one solicitud; `.../crear-borrador-wordpress` triggers
`core.services.wordpress_publication_service.crear_borrador` against the
real WordPress REST API (draft only, never publishes, per
docs/PROJECT_RULES.md rule 1); `.../confirmar-publicacion` (Increment 4)
registers a destino as actually live — required `url_publicacion` for
Facebook/Instagram, optional for WordPress (already has `wp_url`); and
`.../cancelar` cancels a destino that never went out. Both of the latter
two recompute `esta_completa` across the solicitud's destinos and stamp
`fecha_cierre` the first time it becomes true — see
`core.services.publication_request_service.cerrar_si_completa`.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_cms_publisher, get_current_user, get_unit_of_work
from app.api.schemas.destino_publicacion import (
    DestinoPublicacionConfirmarPublicacion,
    DestinoPublicacionCreate,
    DestinoPublicacionOut,
)
from app.api.schemas.publication_request import (
    PublicationRequestCreate,
    PublicationRequestLinkPauta,
    PublicationRequestOut,
    PublicationRequestUpdate,
)
from core.analytics import AnalyticsService
from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.entities.user import User
from core.ports.cms_publisher import CMSPublisher
from core.ports.unit_of_work import UnitOfWork
from core.services.destino_publicacion_service import cancelar, marcar_publicado
from core.services.publication_request_service import (
    aceptar,
    cerrar_si_completa,
    edit_solicitud,
    link_pauta,
)
from core.services.wordpress_publication_service import crear_borrador

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
    completa: bool | None = None,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[PublicationRequest]:
    """Return requests, optionally filtered to a single `estado` (e.g. RECIBIDA)
    and/or by completitud.

    `estado=RECIBIDA` comes back in the editorial team's actual working
    order — prioridad manual, then peso comercial of the linked Pauta,
    then arrival time (see `AnalyticsService.solicitudes_pendientes_priorizadas`)
    — not just insertion order. Every other filter (or no filter) returns
    `list_all`'s own order, unchanged; only the one screen this ordering
    was asked for is affected.

    `completa` (Sprint 4A, Increment 4 UI) filters by `fecha_cierre is
    not None` — the replacement for the retired
    `estado=PublicationRequestStatus.PUBLICADA` the "Publicadas" column
    used before `estado` was reduced to intake triage (see
    `core.entities.publication_request`). There is no server-side
    `esta_completa` query — `fecha_cierre` is set exactly once, the
    moment a solicitud becomes complete, so filtering on it is
    equivalent and does not need to touch `DestinoPublicacion` at all.
    """
    if estado == PublicationRequestStatus.RECIBIDA:
        analytics = AnalyticsService(
            clients=uow.clients.list_all(),
            pautas=uow.pautas.list_all(),
            solicitudes=uow.publication_requests.list_all(),
            destinos=uow.destinos_publicacion.list_all(),
        )
        return analytics.solicitudes_pendientes_priorizadas()
    solicitudes = uow.publication_requests.list_all(estado=estado)
    if completa is True:
        solicitudes = [s for s in solicitudes if s.fecha_cierre is not None]
    elif completa is False:
        solicitudes = [s for s in solicitudes if s.fecha_cierre is None]
    return solicitudes


@router.post("/{request_id}/publish", response_model=PublicationRequestOut)
def publish_publication_request(
    request_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    current_user: User = Depends(get_current_user),
) -> PublicationRequest:
    """Accept a PublicationRequest and mark it published on WordPress (compatibility flow).

    Sprint 4A, Increment 4: this is the original single-click "Publicar"
    action, kept working exactly as before from the operator's point of
    view, now implemented over the multi-destino model instead of a
    `PUBLICADA` estado (retired — see `core.entities.publication_request`).
    Transitions `estado` to `ACEPTADA` (`aceptar`, raises if there is no
    `pauta_id` — the same invariant `PUBLICADA` used to enforce), then
    reuses an existing WORDPRESS destino if the solicitud already has one
    (e.g. from `crear-borrador-wordpress`) or creates a new one, and
    marks it `PUBLICADO`. Any other destinos the solicitud already has
    are included when recomputing `esta_completa`/`fecha_cierre` — this
    endpoint never assumes it is the only way a solicitud gets published.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    aceptada = aceptar(solicitud)
    destinos = uow.destinos_publicacion.list_by_publication_request_id(request_id)
    wordpress_destino = next((d for d in destinos if d.canal == CanalPublicacion.WORDPRESS), None)
    if wordpress_destino is None:
        wordpress_destino = DestinoPublicacion(
            publication_request_id=request_id, canal=CanalPublicacion.WORDPRESS
        )
    else:
        destinos.remove(wordpress_destino)
    publicado = marcar_publicado(wordpress_destino, registrado_por_user_id=current_user.id)
    destinos.append(publicado)
    cerrada = cerrar_si_completa(aceptada, destinos)
    uow.destinos_publicacion.save(publicado)
    uow.publication_requests.save(cerrada)
    uow.commit()
    return cerrada


@router.patch("/{request_id}", response_model=PublicationRequestOut)
def edit_publication_request(
    request_id: str,
    payload: PublicationRequestUpdate,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> PublicationRequest:
    """Correct titulo/texto/prioridad_manual on a still-RECIBIDA PublicationRequest."""
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    editada = edit_solicitud(
        solicitud,
        titulo=payload.titulo,
        texto=payload.texto,
        prioridad_manual=payload.prioridad_manual,
    )
    uow.publication_requests.save(editada)
    uow.commit()
    return editada


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


@router.post("/{request_id}/destinos", response_model=DestinoPublicacionOut, status_code=201)
def create_destino(
    request_id: str,
    payload: DestinoPublicacionCreate,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> DestinoPublicacion:
    """Add a new publication destino (PENDIENTE) to an existing PublicationRequest."""
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    destino = DestinoPublicacion(publication_request_id=request_id, canal=payload.canal)
    uow.destinos_publicacion.save(destino)
    uow.commit()
    return destino


@router.get("/{request_id}/destinos", response_model=list[DestinoPublicacionOut])
def list_destinos(
    request_id: str, uow: UnitOfWork = Depends(get_unit_of_work)
) -> list[DestinoPublicacion]:
    """Return every destino belonging to a PublicationRequest."""
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    return uow.destinos_publicacion.list_by_publication_request_id(request_id)


@router.post(
    "/{request_id}/destinos/{destino_id}/crear-borrador-wordpress",
    response_model=DestinoPublicacionOut,
)
def crear_borrador_wordpress(
    request_id: str,
    destino_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    cms_publisher: CMSPublisher = Depends(get_cms_publisher),
) -> DestinoPublicacion:
    """Create a WordPress draft for `destino_id` and attach its post_id/url.

    Never publishes — only creates a draft (docs/PROJECT_RULES.md rule 1).
    A human still has to go into WordPress, or call
    `confirmar-publicacion`, to actually mark the post live in this system.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    destino = uow.destinos_publicacion.get_by_id(destino_id)
    if destino is None or destino.publication_request_id != request_id:
        raise HTTPException(status_code=404, detail="DestinoPublicacion not found")
    con_borrador = crear_borrador(destino, solicitud, cms_publisher)
    uow.destinos_publicacion.save(con_borrador)
    uow.commit()
    return con_borrador


@router.post(
    "/{request_id}/destinos/{destino_id}/confirmar-publicacion",
    response_model=DestinoPublicacionOut,
)
def confirmar_publicacion_destino(
    request_id: str,
    destino_id: str,
    payload: DestinoPublicacionConfirmarPublicacion,
    uow: UnitOfWork = Depends(get_unit_of_work),
    current_user: User = Depends(get_current_user),
) -> DestinoPublicacion:
    """Confirm a destino is actually live (Sprint 4A, Increment 4).

    Facebook/Instagram register their `url_publicacion` here — the entity
    itself rejects `PUBLICADO` without one for those canales. WordPress
    already has `wp_url` from `crear-borrador-wordpress` and does not
    need one. Recomputes `esta_completa` across every destino of this
    solicitud and stamps `fecha_cierre` the first time it becomes true.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    destinos = uow.destinos_publicacion.list_by_publication_request_id(request_id)
    destino = next((d for d in destinos if d.id == destino_id), None)
    if destino is None:
        raise HTTPException(status_code=404, detail="DestinoPublicacion not found")
    publicado = marcar_publicado(
        destino, registrado_por_user_id=current_user.id, url_publicacion=payload.url_publicacion
    )
    destinos_actualizados = [publicado if d.id == destino_id else d for d in destinos]
    cerrada = cerrar_si_completa(solicitud, destinos_actualizados)
    uow.destinos_publicacion.save(publicado)
    uow.publication_requests.save(cerrada)
    uow.commit()
    return publicado


@router.post(
    "/{request_id}/destinos/{destino_id}/cancelar",
    response_model=DestinoPublicacionOut,
)
def cancelar_destino(
    request_id: str,
    destino_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> DestinoPublicacion:
    """Cancel a destino that never went out (Sprint 4A, Increment 4).

    A `FALLIDO` destino is deliberately cancellable too — see
    `core.services.destino_publicacion_service.cancelar`'s docstring for
    why it must never be a dead end. Recomputes `esta_completa`/
    `fecha_cierre`: cancelling the last still-pending destino can itself
    complete the solicitud.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    destinos = uow.destinos_publicacion.list_by_publication_request_id(request_id)
    destino = next((d for d in destinos if d.id == destino_id), None)
    if destino is None:
        raise HTTPException(status_code=404, detail="DestinoPublicacion not found")
    cancelado = cancelar(destino)
    destinos_actualizados = [cancelado if d.id == destino_id else d for d in destinos]
    cerrada = cerrar_si_completa(solicitud, destinos_actualizados)
    uow.destinos_publicacion.save(cancelado)
    uow.publication_requests.save(cerrada)
    uow.commit()
    return cancelado
