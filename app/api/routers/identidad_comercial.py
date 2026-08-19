"""Routes for IdentidadComercial — la sección Configuración › Identidad comercial.

`PUT` hace upsert (crea o reemplaza) en vez del ciclo POST-then-PUT que
usan las colecciones (`Gasto`, `PlanPauta`): esto es un singleton (ver
`core.entities.identidad_comercial.ID_UNICO`), no hay "crear otro". El
logo vive aparte, en `MediaStorage` — mismo Volume que ya usa `MediaAsset`
(ver `agents/storage/local_disk.py`) — nunca en esta tabla ni en el
navegador, así sobrevive a cualquier dispositivo/sesión.

Every route requires an authenticated session — `dependencies=` at the
`APIRouter` level, same convention as every other router in this package.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.dependencies import get_current_user, get_media_storage, get_unit_of_work
from app.api.schemas.identidad_comercial import IdentidadComercialCreate, IdentidadComercialOut
from core.entities.identidad_comercial import ID_UNICO, IdentidadComercial
from core.ports.media_storage import MediaStorage
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(
    prefix="/identidad-comercial",
    tags=["identidad-comercial"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=IdentidadComercialOut)
def obtener_identidad_comercial(uow: UnitOfWork = Depends(get_unit_of_work)) -> IdentidadComercial:
    """Return the configured commercial identity, or 404 if never set up."""
    identidad = uow.identidad_comercial.get()
    if identidad is None:
        raise HTTPException(status_code=404, detail="IdentidadComercial not configured yet")
    return identidad


@router.put("", response_model=IdentidadComercialOut)
def guardar_identidad_comercial(
    payload: IdentidadComercialCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> IdentidadComercial:
    """Create or replace the text fields of the commercial identity.

    Never touches `logo_storage_key`/`logo_content_type` — those are only
    ever set by `POST /identidad-comercial/logo`, so re-saving the text
    fields never orphans an already-uploaded logo.
    """
    existing = uow.identidad_comercial.get()
    identidad = IdentidadComercial(
        id=ID_UNICO,
        logo_storage_key=existing.logo_storage_key if existing else None,
        logo_content_type=existing.logo_content_type if existing else None,
        **payload.model_dump(),
    )
    uow.identidad_comercial.save(identidad)
    uow.commit()
    return identidad


@router.post("/logo", response_model=IdentidadComercialOut)
async def subir_logo(
    archivo: UploadFile = File(...),
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> IdentidadComercial:
    """Upload (or replace) the commercial identity's logo.

    Requires the text fields to already be configured — same reasoning
    `subir_media` in `app.api.routers.publication_requests` uses for
    requiring the parent solicitud to exist first.
    """
    existing = uow.identidad_comercial.get()
    if existing is None:
        raise HTTPException(
            status_code=404,
            detail="Configura primero los datos de Identidad comercial antes de subir el logo",
        )
    if not (archivo.content_type or "").startswith("image/"):
        raise HTTPException(status_code=422, detail="El logo debe ser una imagen")
    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(status_code=422, detail="El archivo está vacío")

    nueva_key = f"identidad-comercial/logo-{uuid4()}"
    media_storage.guardar(nueva_key, contenido)
    if existing.logo_storage_key:
        media_storage.eliminar(existing.logo_storage_key)

    actualizado = replace(
        existing, logo_storage_key=nueva_key, logo_content_type=archivo.content_type or "image/png"
    )
    uow.identidad_comercial.save(actualizado)
    uow.commit()
    return actualizado


@router.get("/logo")
def descargar_logo(
    uow: UnitOfWork = Depends(get_unit_of_work),
    media_storage: MediaStorage = Depends(get_media_storage),
) -> Response:
    """Stream the configured logo's raw bytes — used as an `<img>` src and by
    `app.api.pdf_informe` to embed the logo in a generated PDF."""
    identidad = uow.identidad_comercial.get()
    if identidad is None or identidad.logo_storage_key is None:
        raise HTTPException(status_code=404, detail="No hay logo configurado")
    try:
        contenido = media_storage.leer(identidad.logo_storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Logo content not found") from exc
    return Response(
        content=contenido, media_type=identidad.logo_content_type or "application/octet-stream"
    )
