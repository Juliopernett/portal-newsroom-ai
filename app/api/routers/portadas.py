"""Route for rendering a branded news cover (portada).

Sprint Portadas (2026-10-29). `POST /portadas` takes a base photo (and,
optionally, a second photo for the highlight-circle template) plus the
headline, and returns the finished 1080x1350 cover — the same image goes
on WordPress and on social networks. Nothing is stored: the operator
previews the result and downloads it. See
`agents.images.pillow_portada_renderer` for the template details.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile

from app.api.dependencies import get_current_user, get_portada_renderer
from config.settings import get_settings
from core.ports.portada_renderer import PortadaRenderer, SolicitudPortada, VariantePortada
from core.services.media_asset_service import TIPOS_IMAGEN_PERMITIDOS

router = APIRouter(
    prefix="/portadas",
    tags=["portadas"],
    dependencies=[Depends(get_current_user)],
)


def leer_imagen_subida(archivo: UploadFile, nombre: str) -> bytes:
    if (archivo.content_type or "") not in TIPOS_IMAGEN_PERMITIDOS:
        raise HTTPException(status_code=415, detail=f"La {nombre} debe ser JPG, PNG, WEBP o GIF")
    contenido = archivo.file.read()
    if len(contenido) > get_settings().media_max_bytes_imagen:
        raise HTTPException(status_code=413, detail=f"La {nombre} es demasiado pesada")
    return contenido


@router.post("", response_class=Response, responses={200: {"content": {"image/png": {}}}})
def generar_portada(
    imagen_base: UploadFile = File(...),
    titular: str = Form(..., min_length=1, max_length=200),
    variante: VariantePortada = Form(VariantePortada.NOTICIAS),
    antetitulo: str | None = Form(None, max_length=60),
    imagen_circulo: UploadFile | None = File(None),
    enfoque_x: float = Form(0.5, ge=0, le=1),
    enfoque_y: float = Form(0.3, ge=0, le=1),
    formato: str = Form("png", pattern="^(png|jpeg)$"),
    renderer: PortadaRenderer = Depends(get_portada_renderer),
) -> Response:
    """Render a cover and return it as an image (`png` or `jpeg`).

    Sending `imagen_circulo` selects the two-photo template (highlight
    circle + arrow). 415/413 for a non-image or oversized upload, 422 for
    an unreadable image or an empty headline.
    """
    solicitud = SolicitudPortada(
        imagen_base=leer_imagen_subida(imagen_base, "imagen base"),
        titular=titular,
        variante=variante,
        antetitulo=antetitulo or None,
        imagen_circulo=(
            leer_imagen_subida(imagen_circulo, "imagen del círculo")
            if imagen_circulo is not None and imagen_circulo.filename
            else None
        ),
        enfoque_x=enfoque_x,
        enfoque_y=enfoque_y,
    )
    contenido = renderer.renderizar(solicitud, formato=formato)
    return Response(
        content=contenido,
        media_type="image/jpeg" if formato == "jpeg" else "image/png",
        headers={"Content-Disposition": f'inline; filename="portada.{formato}"'},
    )
