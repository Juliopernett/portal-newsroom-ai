"""Routes for PublicationRequest.

`POST /{request_id}/publish` (reworked Sprint 4A, Increment 4) is the
pre-multi-destino "Publicar" flow, kept working unchanged from the
operator's point of view: it accepts the request (`estado` → `ACEPTADA`,
same `pauta_id`-required invariant `PUBLICADA` used to enforce) and
creates/marks a compatibility WordPress destino as `PUBLICADO`. See
`publish_publication_request`'s own docstring.

`POST /{request_id}/cancelar` (2026-08-14) exposes `cancelar_solicitud` --
closes a request the client asked to cancel before it went out. Only
valid from RECIBIDA, same restriction `PATCH` already applies and for
the same reason.

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

`GET /{request_id}/reporte` (Incremento 6) exposes
`core.services.reporte_service.construir_reporte` — enlaces por
plataforma, fecha de publicación, estado y si consumió cuota de Pauta.
Generación automática (se arma en el momento en que se pide); el envío
al cliente sigue siendo manual, no hay integración de envío en este
sprint.

`/{request_id}/media` (Incremento 7 — see
docs/adr/ADR-007-media-assets.md) exposes `MediaAsset` CRUD scoped to
one solicitud: `POST` uploads a file (`multipart/form-data`, rejected
with 409 once the solicitud is `completa` — see Decision 4), `GET`
lists metadata only, `GET .../{media_id}/contenido` streams the actual
bytes back (authenticated — never a public URL, see Decision 2), and
`DELETE` removes one manually before the automatic purge
(`scripts/purgar_media_expirados.py`) reaches it.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, not per-function, so a route added here later is
protected automatically instead of by remembering to add it.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.dependencies import (
    get_cms_publisher,
    get_current_user,
    get_media_storage,
    get_unit_of_work,
)
from app.api.schemas.destino_publicacion import (
    DestinoPublicacionConfirmarPublicacion,
    DestinoPublicacionCorregirEnlace,
    DestinoPublicacionCreate,
    DestinoPublicacionOut,
)
from app.api.schemas.media_asset import MediaAssetOut
from app.api.schemas.publication_request import (
    PublicationRequestCreate,
    PublicationRequestLinkPauta,
    PublicationRequestOut,
    PublicationRequestUpdate,
)
from app.api.schemas.reporte import ReporteSolicitudOut
from config.settings import get_settings
from core.analytics import AnalyticsService
from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion
from core.entities.media_asset import MediaAsset
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.entities.user import User
from core.ports.cms_publisher import CMSPublisher
from core.ports.media_storage import MediaStorage
from core.ports.unit_of_work import UnitOfWork
from core.services.destino_publicacion_service import (
    cancelar,
    corregir_enlace,
    marcar_publicado,
    puede_eliminarse_sin_afectar_completitud,
)
from core.services.media_asset_service import (
    construir_storage_key,
    determinar_tipo,
    validar_tamano,
)
from core.services.publication_request_service import (
    aceptar,
    cancelar_solicitud,
    cerrar_si_completa,
    edit_solicitud,
    link_pauta,
)
from core.services.reporte_service import ReporteSolicitud, construir_reporte
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


@router.get("/sin-destino-social", response_model=list[PublicationRequestOut])
def list_sin_destino_social(
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> list[PublicationRequest]:
    """Return publicadas of a vigente Pauta with no Facebook/Instagram destino yet.

    Backs the "Sin destino (contratos activos)" filter in Solicitudes.
    One query per repository (same shape `/dashboard/resumen` already
    uses), computed in `AnalyticsService.solicitudes_sin_destino_social`
    — replaces what used to be one `GET .../destinos` call per candidate
    solicitud from the frontend (up to ~180 concurrent requests, enough
    to saturate the connection pool and even knock out an unrelated
    `/auth/me` check mid-burst, 2026-08-20) with this single endpoint.
    """
    analytics = AnalyticsService(
        clients=uow.clients.list_all(),
        pautas=uow.pautas.list_all(),
        solicitudes=uow.publication_requests.list_all(),
        destinos=uow.destinos_publicacion.list_all(),
    )
    return analytics.solicitudes_sin_destino_social()


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


@router.post("/{request_id}/cancelar", response_model=PublicationRequestOut)
def cancel_publication_request(
    request_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> PublicationRequest:
    """Cancel a still-RECIBIDA PublicationRequest that will never be published.

    Raises via `cancelar_solicitud` (422, see `app.api.errors`) if the
    request already moved past RECIBIDA.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    cancelada = cancelar_solicitud(solicitud)
    uow.publication_requests.save(cancelada)
    uow.commit()
    return cancelada


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
        destino,
        registrado_por_user_id=current_user.id,
        url_publicacion=payload.url_publicacion,
        meta_post_id=payload.meta_post_id,
    )
    destinos_actualizados = [publicado if d.id == destino_id else d for d in destinos]
    cerrada = cerrar_si_completa(solicitud, destinos_actualizados)
    uow.destinos_publicacion.save(publicado)
    uow.publication_requests.save(cerrada)
    uow.commit()
    return publicado


@router.patch(
    "/{request_id}/destinos/{destino_id}/corregir-enlace",
    response_model=DestinoPublicacionOut,
)
def corregir_enlace_destino(
    request_id: str,
    destino_id: str,
    payload: DestinoPublicacionCorregirEnlace,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> DestinoPublicacion:
    """Fix a data-entry mistake on an already-`PUBLICADO` destino's link.

    Unlike `confirmar_publicacion_destino`, this never touches `estado`,
    `fecha_publicacion`, or the parent solicitud's `fecha_cierre` — the
    destino was already correctly counted as consumiendo cuota; only the
    link itself was wrong. See
    `core.services.destino_publicacion_service.corregir_enlace`.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    destinos = uow.destinos_publicacion.list_by_publication_request_id(request_id)
    destino = next((d for d in destinos if d.id == destino_id), None)
    if destino is None:
        raise HTTPException(status_code=404, detail="DestinoPublicacion not found")
    corregido = corregir_enlace(
        destino,
        wp_url=payload.wp_url,
        url_publicacion=payload.url_publicacion,
        meta_post_id=payload.meta_post_id,
    )
    uow.destinos_publicacion.save(corregido)
    uow.commit()
    return corregido


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


@router.delete("/{request_id}/destinos/{destino_id}", status_code=204)
def eliminar_destino(
    request_id: str,
    destino_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> None:
    """Delete a redundant destino — never a genuine publication.

    Not a state transition (`cancelar` already covers walking back a
    destino that hasn't gone out); this is for a row that should not have
    existed as a separate destino at all — the clearest case being the
    WordPress placeholder `publish_publication_request` stamps on every
    solicitud for compatibility with the old single-click flow, once a
    real Facebook/Instagram destino already covers the same solicitud.
    `puede_eliminarse_sin_afectar_completitud` is the one guard: refuses
    (`ValueError` → 422) if deleting `destino_id` would change
    `esta_completa` for what's left, so this can never silently reopen a
    solicitud, clear its `fecha_cierre`, or un-consume a pauta's cupo.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    destinos = uow.destinos_publicacion.list_by_publication_request_id(request_id)
    destino = next((d for d in destinos if d.id == destino_id), None)
    if destino is None:
        raise HTTPException(status_code=404, detail="DestinoPublicacion not found")
    otros = [d for d in destinos if d.id != destino_id]
    if not puede_eliminarse_sin_afectar_completitud(destino, otros):
        raise ValueError(
            "no se puede eliminar: dejaría la solicitud sin completar o la completaría "
            "sin una publicación real"
        )
    uow.destinos_publicacion.delete(destino_id)
    uow.commit()


@router.get("/{request_id}/reporte", response_model=ReporteSolicitudOut)
def obtener_reporte(
    request_id: str, uow: UnitOfWork = Depends(get_unit_of_work)
) -> ReporteSolicitud:
    """Return `request_id`'s report: enlaces por plataforma, fecha de
    publicación, estado y si consumió cuota de Pauta (Sprint 4A, Incremento 6).

    Generación automática — se arma en el momento en que se pide, nunca
    se guarda. El cliente (nombre) solo se resuelve cuando la solicitud
    tiene `pauta_id`; sin Pauta vinculada el reporte igual se arma, solo
    que sin `cliente_nombre`.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    destinos = uow.destinos_publicacion.list_by_publication_request_id(request_id)
    cliente = None
    if solicitud.pauta_id is not None:
        pauta = uow.pautas.get_by_id(solicitud.pauta_id)
        if pauta is not None:
            cliente = uow.clients.get_by_id(pauta.client_id)
    return construir_reporte(solicitud, destinos, cliente)


@router.post("/{request_id}/media", response_model=MediaAssetOut, status_code=201)
async def subir_media(
    request_id: str,
    archivo: UploadFile = File(...),
    uow: UnitOfWork = Depends(get_unit_of_work),
    current_user: User = Depends(get_current_user),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> MediaAsset:
    """Attach a file (imagen o video) to a PublicationRequest (Incremento 7).

    Rejects (409) once the solicitud is `completa` — no reason to attach
    material to something already resolved on every destino, and it keeps
    `scripts/purgar_media_expirados.py`'s job well-defined. `tipo` is
    derived from `archivo.content_type`, never trusted from the client as
    a separate field.
    """
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    if solicitud.fecha_cierre is not None:
        raise HTTPException(
            status_code=409, detail="PublicationRequest is already completa — cannot attach media"
        )
    settings = get_settings()
    tipo = determinar_tipo(archivo.content_type or "")
    contenido = await archivo.read()
    validar_tamano(
        tipo,
        len(contenido),
        max_bytes_imagen=settings.media_max_bytes_imagen,
        max_bytes_video=settings.media_max_bytes_video,
    )
    media_id = str(uuid4())
    media = MediaAsset(
        id=media_id,
        publication_request_id=request_id,
        tipo=tipo,
        nombre_archivo=archivo.filename or "archivo",
        content_type=archivo.content_type or "",
        tamano_bytes=len(contenido),
        storage_key=construir_storage_key(request_id, media_id),
        subido_por_user_id=current_user.id,
    )
    media_storage.guardar(media.storage_key, contenido)
    uow.media_assets.save(media)
    uow.commit()
    return media


@router.get("/{request_id}/media", response_model=list[MediaAssetOut])
def list_media(request_id: str, uow: UnitOfWork = Depends(get_unit_of_work)) -> list[MediaAsset]:
    """Return every media asset attached to a PublicationRequest (metadata only)."""
    solicitud = uow.publication_requests.get_by_id(request_id)
    if solicitud is None:
        raise HTTPException(status_code=404, detail="PublicationRequest not found")
    return uow.media_assets.list_by_publication_request_id(request_id)


@router.get("/{request_id}/media/{media_id}/contenido")
def descargar_media(
    request_id: str,
    media_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> Response:
    """Stream a MediaAsset's raw file content — authenticated, never a public URL."""
    media = uow.media_assets.get_by_id(media_id)
    if media is None or media.publication_request_id != request_id:
        raise HTTPException(status_code=404, detail="MediaAsset not found")
    try:
        contenido = media_storage.leer(media.storage_key)
    except FileNotFoundError as exc:
        # The DB row survived but the underlying file did not (manual disk
        # cleanup, volume reset, ...) — a 404 is more actionable than an
        # opaque 500 for what is still "this content isn't there".
        raise HTTPException(status_code=404, detail="MediaAsset content not found") from exc
    return Response(
        content=contenido,
        media_type=media.content_type,
        headers={"Content-Disposition": f'inline; filename="{media.nombre_archivo}"'},
    )


@router.delete("/{request_id}/media/{media_id}", status_code=204)
def eliminar_media(
    request_id: str,
    media_id: str,
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> None:
    """Manually delete a MediaAsset before the automatic purge reaches it."""
    media = uow.media_assets.get_by_id(media_id)
    if media is None or media.publication_request_id != request_id:
        raise HTTPException(status_code=404, detail="MediaAsset not found")
    media_storage.eliminar(media.storage_key)
    uow.media_assets.delete(media_id)
    uow.commit()
