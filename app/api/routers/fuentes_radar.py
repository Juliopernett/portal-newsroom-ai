"""Routes to manage Radar sources and trigger a scan (Sprint Fuentes, 2026-10-29).

`GET/POST/PATCH /radar-fuentes` is the editable list of places the Radar
scans (see `core.entities.source.Source`). `POST /radar-fuentes/probar`
previews what an address would give — nothing is saved. `POST
/radar-fuentes/escanear` is the "Escanear ahora" button: it scans every
enabled source right away (ignoring each one's interval); the hourly run
is `scripts/escanear_fuentes.py`, which only scans what is due.

Only one scan may run at a time per process (409 otherwise): two clicks —
or a click during the cron run — would just double the network and
database work for the same result.
"""

from __future__ import annotations

import re
import threading
import unicodedata
from collections.abc import Callable
from dataclasses import replace
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    get_current_user,
    get_detector_feed,
    get_fabrica_adaptadores,
    get_unit_of_work,
)
from app.api.schemas.fuente_radar import (
    EntradaPreviaOut,
    EscaneoOut,
    FuenteRadarCreate,
    FuenteRadarOut,
    FuenteRadarUpdate,
    ProbarFuenteIn,
    ProbarFuenteOut,
    ResultadoEscaneoOut,
)
from core.entities.source import Source
from core.ports.content_source import ContentSource
from core.ports.feed_detector import FeedDetector, FeedDetectorError
from core.ports.unit_of_work import UnitOfWork
from core.services.source_scan_service import ESTADO_OK, escanear_fuentes

router = APIRouter(
    prefix="/radar-fuentes",
    tags=["radar-fuentes"],
    dependencies=[Depends(get_current_user)],
)

_ESCANEO_EN_CURSO = threading.Lock()


def _slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower()).strip("-")[:40] or "fuente"


def _nombre_corto(titulo: str, feed_url: str) -> str:
    """The site's title if short, else its domain (Blogger titles are whole sentences)."""
    titulo = titulo.strip()
    if 0 < len(titulo) <= 40:
        return titulo
    return (urlparse(feed_url).hostname or feed_url).removeprefix("www.")


def _get_or_404(uow: UnitOfWork, source_id: str) -> Source:
    fuente = uow.sources.get_by_id(source_id)
    if fuente is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    return fuente


@router.get("", response_model=list[FuenteRadarOut])
def list_fuentes(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[Source]:
    """Return every configured source with its last scan result."""
    return uow.sources.list_all()


@router.post("/probar", response_model=ProbarFuenteOut)
def probar_fuente(
    payload: ProbarFuenteIn, detector: FeedDetector = Depends(get_detector_feed)
) -> ProbarFuenteOut:
    """Find the feed behind an address and show its latest entries — saves nothing."""
    try:
        feed = detector.detectar(payload.url)
    except FeedDetectorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if feed is None:
        raise HTTPException(status_code=422, detail="No se encontró un feed RSS en esa dirección")
    return ProbarFuenteOut(
        feed_url=feed.feed_url,
        titulo=feed.titulo,
        entradas=[EntradaPreviaOut(titulo=e.titulo, publicada=e.publicada) for e in feed.entradas],
    )


@router.post("", response_model=FuenteRadarOut, status_code=201)
def crear_fuente(
    payload: FuenteRadarCreate,
    uow: UnitOfWork = Depends(get_unit_of_work),
    detector: FeedDetector = Depends(get_detector_feed),
) -> Source:
    """Add a source from a site or feed address (the feed is detected for you)."""
    try:
        feed = detector.detectar(payload.url)
    except FeedDetectorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if feed is None:
        raise HTTPException(status_code=422, detail="No se encontró un feed RSS en esa dirección")
    if any(f.url == feed.feed_url for f in uow.sources.list_all()):
        raise HTTPException(status_code=409, detail="Esa fuente ya está configurada")
    nombre = (payload.name or _nombre_corto(feed.titulo, feed.feed_url)).strip()
    fuente = Source(
        id=f"fuente-{_slug(nombre)}-{uuid4().hex[:6]}",
        name=nombre,
        type="rss",
        url=feed.feed_url,
        intervalo_minutos=payload.intervalo_minutos,
        max_items=payload.max_items,
        max_age_days=payload.max_age_days,
    )
    uow.sources.save(fuente)
    uow.commit()
    return fuente


@router.patch("/{source_id}", response_model=FuenteRadarOut)
def editar_fuente(
    source_id: str, payload: FuenteRadarUpdate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> Source:
    """Enable/disable a source or change its name and scan limits."""
    cambios = payload.model_dump(exclude_none=True)
    fuente = replace(_get_or_404(uow, source_id), **cambios)
    if cambios.get("enabled") is True:
        # Re-enabling a source that was failing: start clean, not in backoff.
        fuente = replace(fuente, errores_consecutivos=0, last_error=None)
    uow.sources.save(fuente)
    uow.commit()
    return fuente


@router.post("/escanear", response_model=EscaneoOut)
def escanear_ahora(
    uow: UnitOfWork = Depends(get_unit_of_work),
    fabrica: Callable[[Source], ContentSource] = Depends(get_fabrica_adaptadores),
) -> EscaneoOut:
    """Scan every enabled source right now and report what each one found."""
    if not _ESCANEO_EN_CURSO.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ya hay un escaneo en curso")
    try:
        resultados = escanear_fuentes(uow, fabrica, forzar=True)
    finally:
        _ESCANEO_EN_CURSO.release()
    return EscaneoOut(
        resultados=[ResultadoEscaneoOut.model_validate(r) for r in resultados],
        nuevos_total=sum(r.nuevos for r in resultados if r.estado == ESTADO_OK),
    )
