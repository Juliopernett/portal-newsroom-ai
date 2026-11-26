"""Routes for Configuración › Colores: the colours of covers and Radar cards.

`GET` always answers: until someone saves their own, it returns the website's
colours (the entity's defaults).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from agents.images.muestra_marca import portada_de_muestra, radar_de_muestra
from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.colores_marca import ColoresMarcaIn, ColoresMarcaOut
from core.entities.colores_marca import ColoresMarca
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(
    prefix="/colores-marca", tags=["colores-marca"], dependencies=[Depends(get_current_user)]
)

_PATRON = r"^#[0-9A-Fa-f]{6}$"


@router.get("", response_model=ColoresMarcaOut)
def obtener_colores(uow: UnitOfWork = Depends(get_unit_of_work)) -> ColoresMarca:
    """Return the colours in use."""
    return uow.colores_marca.get() or ColoresMarca()


@router.put("", response_model=ColoresMarcaOut)
def guardar_colores(
    payload: ColoresMarcaIn, uow: UnitOfWork = Depends(get_unit_of_work)
) -> ColoresMarca:
    """Save the colours; every image generated from now on uses them."""
    colores = ColoresMarca(**payload.model_dump())
    uow.colores_marca.save(colores)
    uow.commit()
    return colores


@router.get("/vista-previa")
def vista_previa(
    pieza: Literal["portada", "radar"],
    fondo: str = Query(pattern=_PATRON),
    destacado: str = Query(pattern=_PATRON),
    texto_destacado: str = Query(pattern=_PATRON),
) -> Response:
    """A sample cover or Radar card with colours that are not saved yet."""
    colores = ColoresMarca(fondo=fondo, destacado=destacado, texto_destacado=texto_destacado)
    dibujar = portada_de_muestra if pieza == "portada" else radar_de_muestra
    return Response(content=dibujar(colores), media_type="image/png")
