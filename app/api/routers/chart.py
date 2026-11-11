"""Routes for the Chart Vallenato.

The backend prefix is `/chart-vallenato` (not `/chart`) so it never collides
with a React Router path. Every route requires a session except
`GET /chart-vallenato/publico.json` (see `router_publico`): the website's
sidebar widget reads it from the browser of any visitor, and it carries only
public data (titles, positions, public view counts).
"""

from __future__ import annotations

import html
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse

from app.api.dependencies import (
    get_current_user,
    get_settings_dep,
    get_unit_of_work,
    get_youtube_reader,
)
from app.api.schemas.chart import (
    CanalIn,
    CanalOut,
    ChartOut,
    ChartPublicoOut,
    EdicionOut,
    EdicionResumenOut,
    EstadoSemanalOut,
    FilaChartOut,
    FilaEdicionOut,
    RecoleccionOut,
    VideoManualIn,
    VideoPatch,
    VideoSeguidoOut,
)
from config.settings import Settings
from core.entities.chart import CanalChart, EdicionChart, FilaEdicion, VideoChart
from core.ports.unit_of_work import UnitOfWork
from core.ports.youtube_reader import YouTubeError, YouTubeReader
from core.services.chart_semanal_service import (
    EdicionPublicadaError,
    estado_semanal,
    generar_edicion,
    publicar_edicion,
)
from core.services.chart_service import (
    DIAS_VENTANA,
    TOP_POR_DEFECTO,
    PosicionChart,
    _vistas_ganadas,
    calcular_chart,
    recolectar_chart,
)

router = APIRouter(
    prefix="/chart-vallenato", tags=["chart"], dependencies=[Depends(get_current_user)]
)
router_publico = APIRouter(prefix="/chart-vallenato", tags=["chart"])

_ORIGENES_PUBLICOS = ("https://portalvallenato.com", "https://www.portalvallenato.com")
_HISTORIAL_DIAS = 30
# Max videos listed for the editor's exclude/pin screen. The chart itself always
# ranks every tracked video; this only bounds the size of that response.
_MAX_VIDEOS_LISTADOS = 3000


def _hoy() -> date:
    return datetime.now(UTC).date()


def _fila(p: PosicionChart) -> FilaChartOut:
    return FilaChartOut(
        posicion=p.posicion,
        video_id=p.video.video_id,
        titulo=p.video.titulo,
        artista=p.video.artista,
        miniatura_url=p.video.miniatura_url,
        url=p.video.url,
        vistas_semana=p.vistas_semana,
        vistas_totales=p.vistas_totales,
        tendencia=p.tendencia.value if p.tendencia else None,
        posicion_anterior=p.posicion_anterior,
        fijado=p.fijado,
        parcial=p.parcial,
    )


def _fila_edicion(f: FilaEdicion) -> FilaChartOut:
    return FilaChartOut(**asdict(f), parcial=False)


def _ultima_publicada(uow: UnitOfWork) -> EdicionChart | None:
    """The newest published weekly edition — the only thing the public ever sees."""
    return uow.chart.ultima_publicada_antes(date.max)


def _calcular(uow: UnitOfWork) -> tuple[list[VideoChart], list[PosicionChart], date | None, dict]:
    hoy = _hoy()
    videos = uow.chart.list_videos()
    snaps = uow.chart.list_snapshots(
        [v.video_id for v in videos], desde=hoy - timedelta(days=_HISTORIAL_DIAS)
    )
    ultimo = max((s.fecha for lista in snaps.values() for s in lista), default=None)
    return videos, calcular_chart(videos, snaps, hoy, top=TOP_POR_DEFECTO), ultimo, snaps


@router.get("", response_model=ChartOut)
def obtener_chart(
    uow: UnitOfWork = Depends(get_unit_of_work),
    settings: Settings = Depends(get_settings_dep),
) -> ChartOut:
    """The computed top 10 plus every tracked video (for the exclude/pin controls)."""
    videos, filas, ultimo, snaps = _calcular(uow)
    hoy = _hoy()
    seguidos = []
    for v in videos[:_MAX_VIDEOS_LISTADOS]:
        r = _vistas_ganadas(snaps.get(v.video_id, []), hoy, DIAS_VENTANA)
        seguidos.append(
            VideoSeguidoOut(
                video_id=v.video_id,
                titulo=v.titulo,
                artista=v.artista,
                url=v.url,
                manual=v.manual,
                excluido=v.excluido,
                es_short=v.es_short,
                duracion_segundos=v.duracion_segundos,
                fijado_posicion=v.fijado_posicion,
                vistas_semana=r[0] if r else None,
            )
        )
    return ChartOut(
        actualizado=ultimo,
        youtube_configurado=bool(settings.youtube_api_key),
        filas=[_fila(p) for p in filas],
        videos=seguidos,
    )


@router.post("/recolectar", response_model=RecoleccionOut)
def recolectar_ahora(
    uow: UnitOfWork = Depends(get_unit_of_work),
    reader: YouTubeReader = Depends(get_youtube_reader),
) -> RecoleccionOut:
    """Run the daily collection now (the cron does the same every day)."""
    res = recolectar_chart(uow, reader)
    uow.commit()
    return RecoleccionOut(
        canales_ok=res.canales_ok,
        canales_con_error=res.canales_con_error,
        videos_nuevos=res.videos_nuevos,
        videos_seguidos=res.videos_seguidos,
        snapshots=res.snapshots,
        error_estadisticas=res.error_estadisticas,
    )


def _edicion_out(e: EdicionChart) -> EdicionOut:
    return EdicionOut(
        semana_fin=e.semana_fin,
        estado=e.estado,
        filas=len(e.filas),
        sin_base=e.sin_base,
        generada_en=e.generada_en,
        publicada_en=e.publicada_en,
        filas_detalle=[FilaEdicionOut(**asdict(f)) for f in e.filas],
    )


@router.get("/estado-semanal", response_model=EstadoSemanalOut)
def obtener_estado_semanal(uow: UnitOfWork = Depends(get_unit_of_work)) -> EstadoSemanalOut:
    """Did this week's close run, and is an edition waiting for review?"""
    e = estado_semanal(uow)
    return EstadoSemanalOut(semana_fin=e.semana_fin, nivel=e.nivel, mensaje=e.mensaje)


@router.get("/ediciones", response_model=list[EdicionResumenOut])
def listar_ediciones(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[EdicionResumenOut]:
    """Weekly editions, newest first. A draft waits here for the editor's review."""
    return [
        EdicionResumenOut(
            semana_fin=e.semana_fin,
            estado=e.estado,
            filas=len(e.filas),
            sin_base=e.sin_base,
            generada_en=e.generada_en,
            publicada_en=e.publicada_en,
        )
        for e in uow.chart.list_ediciones()
    ]


@router.get("/ediciones/{semana_fin}", response_model=EdicionOut)
def obtener_edicion(semana_fin: date, uow: UnitOfWork = Depends(get_unit_of_work)) -> EdicionOut:
    edicion = uow.chart.get_edicion(semana_fin)
    if edicion is None:
        raise HTTPException(status_code=404, detail="Edition not found")
    return _edicion_out(edicion)


@router.post("/ediciones/{semana_fin}/regenerar", response_model=EdicionOut)
def regenerar_edicion(semana_fin: date, uow: UnitOfWork = Depends(get_unit_of_work)) -> EdicionOut:
    """Rebuild a draft after the editor excluded or pinned videos (never a published one)."""
    try:
        edicion = generar_edicion(uow, semana_fin)
    except EdicionPublicadaError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if edicion is None:
        raise HTTPException(status_code=404, detail="No hay cierres suficientes para esa semana")
    uow.commit()
    return _edicion_out(edicion)


@router.post("/ediciones/{semana_fin}/publicar", response_model=EdicionOut)
def publicar(semana_fin: date, uow: UnitOfWork = Depends(get_unit_of_work)) -> EdicionOut:
    try:
        edicion = publicar_edicion(uow, semana_fin)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Edition not found") from exc
    uow.commit()
    return _edicion_out(edicion)


@router.get("/canales", response_model=list[CanalOut])
def listar_canales(uow: UnitOfWork = Depends(get_unit_of_work)) -> list[CanalChart]:
    return uow.chart.list_canales()


@router.post("/canales", response_model=CanalOut, status_code=201)
def agregar_canal(
    payload: CanalIn,
    uow: UnitOfWork = Depends(get_unit_of_work),
    reader: YouTubeReader = Depends(get_youtube_reader),
) -> CanalChart:
    """Follow a channel: paste its address, `@usuario` or `UC…` id."""
    try:
        resuelto = reader.resolver_canal(payload.referencia)
    except YouTubeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    canal = CanalChart(
        canal_id=resuelto.canal_id, nombre=resuelto.nombre, artista=payload.artista or None
    )
    uow.chart.save_canal(canal)
    uow.commit()
    return canal


@router.delete("/canales/{canal_id}", status_code=204)
def quitar_canal(canal_id: str, uow: UnitOfWork = Depends(get_unit_of_work)) -> None:
    if uow.chart.get_canal(canal_id) is None:
        raise HTTPException(status_code=404, detail="Canal not found")
    uow.chart.delete_canal(canal_id)
    uow.commit()


@router.post("/videos", response_model=VideoSeguidoOut, status_code=201)
def agregar_video_manual(
    payload: VideoManualIn,
    uow: UnitOfWork = Depends(get_unit_of_work),
    reader: YouTubeReader = Depends(get_youtube_reader),
) -> VideoSeguidoOut:
    """Track one video by hand (any channel — the list stays open)."""
    try:
        yt = reader.obtener_video(payload.referencia)
    except YouTubeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    video = VideoChart(
        video_id=yt.video_id,
        canal_id=yt.canal_id,
        titulo=yt.titulo,
        artista=payload.artista or None,
        publicado_en=yt.publicado_en,
        miniatura_url=yt.miniatura_url,
        manual=True,
    )
    uow.chart.save_video(video)
    uow.commit()
    return VideoSeguidoOut(
        video_id=video.video_id,
        titulo=video.titulo,
        artista=video.artista,
        url=video.url,
        manual=True,
        excluido=False,
        es_short=video.es_short,
        duracion_segundos=video.duracion_segundos,
        fijado_posicion=None,
        vistas_semana=None,
    )


@router.patch("/videos/{video_id}", response_model=VideoSeguidoOut)
def decidir_video(
    video_id: str, payload: VideoPatch, uow: UnitOfWork = Depends(get_unit_of_work)
) -> VideoSeguidoOut:
    """Exclude/include a video or pin it to a chart position (the editor's veto)."""
    video = uow.chart.get_video(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    cambios: dict[str, object] = {}
    if payload.excluido is not None:
        cambios["excluido"] = payload.excluido
        if payload.excluido:
            cambios["fijado_posicion"] = None  # an excluded video can't stay pinned
    if payload.quitar_fijo:
        cambios["fijado_posicion"] = None
    if payload.fijar_en is not None:
        # Only one video per position: free it if another one holds it.
        for otro in uow.chart.list_videos():
            if otro.fijado_posicion == payload.fijar_en and otro.video_id != video_id:
                uow.chart.save_video(replace(otro, fijado_posicion=None))
        cambios["fijado_posicion"] = payload.fijar_en
        cambios["excluido"] = False
    video = replace(video, **cambios)  # type: ignore[arg-type]
    uow.chart.save_video(video)
    uow.commit()
    return VideoSeguidoOut(
        video_id=video.video_id,
        titulo=video.titulo,
        artista=video.artista,
        url=video.url,
        manual=video.manual,
        excluido=video.excluido,
        es_short=video.es_short,
        duracion_segundos=video.duracion_segundos,
        fijado_posicion=video.fijado_posicion,
        vistas_semana=None,
    )


@router_publico.get("/publico.json", response_model=ChartPublicoOut)
def chart_publico(
    request: Request,
    response: Response,
    uow: UnitOfWork = Depends(get_unit_of_work),
    n: int = Query(default=10, ge=1, le=20, description="Cuántas posiciones devolver"),
) -> ChartPublicoOut:
    """The last published weekly edition (top `n`) — unauthenticated, cacheable.

    Empty until the editor publishes the first edition; the live ranking is
    never exposed here.
    """
    edicion = _ultima_publicada(uow)
    origen = request.headers.get("origin", "")
    response.headers["Cache-Control"] = "public, max-age=900"
    response.headers["Access-Control-Allow-Origin"] = (
        origen if origen in _ORIGENES_PUBLICOS else _ORIGENES_PUBLICOS[0]
    )
    response.headers["Vary"] = "Origin"
    return ChartPublicoOut(
        actualizado=edicion.semana_fin if edicion else None,
        semana_fin=edicion.semana_fin if edicion else None,
        publicada_en=edicion.publicada_en if edicion else None,
        filas=[_fila_edicion(f) for f in edicion.filas][:n] if edicion else [],
    )


_URL_PAGINA_CHART = "https://portalvallenato.com/chart-vallenato/"
_URL_PRIVACIDAD = "https://portalvallenato.com/politica-de-privacidad/"
_CSP_EMBED = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; frame-ancestors *"
)
_FLECHAS = {
    "sube": ("▲", "#1a9d4a"),
    "baja": ("▼", "#d33a2c"),
    "igual": ("=", "#8a97a6"),
    "nuevo": ("NEW", "#e0a100"),
}
_CSS_EMBED = (
    "body{margin:0;font-family:Roboto,Arial,sans-serif;background:#fff;color:#1c2733}"
    ".t{margin:0;padding:10px 12px;background:#3B5998;color:#fff;font-weight:700;text-transform:uppercase;"  # noqa: E501
    "letter-spacing:-.5px;font-size:16px}.t small{display:block;font-weight:400;text-transform:none;"  # noqa: E501
    "letter-spacing:0;font-size:12px;opacity:.85;margin-top:2px}"
    "ol{list-style:none;margin:0;padding:0}li{border-top:1px solid #e3e8ef}"
    "a{color:inherit;text-decoration:none}li a{display:flex;align-items:center;gap:8px;padding:8px 10px}"  # noqa: E501
    "li a:hover{background:#f2f6fb}.n{flex:0 0 26px;text-align:center;font-weight:700;font-size:18px;color:#3B5998}"  # noqa: E501
    ".i{flex:0 0 56px;height:42px;object-fit:cover;background:#dde3ec}.x{flex:1;min-width:0}"
    ".s{display:block;font-weight:600;font-size:13px;line-height:1.25}"
    ".a{display:block;font-size:12px;color:#5c6b7a;margin-top:2px}"
    ".d{flex:0 0 30px;text-align:center;font-size:13px;font-weight:700}"
    ".v{padding:16px 12px;font-size:13px;color:#5c6b7a}"
    ".f{padding:8px 12px;font-size:11px;color:#5c6b7a;border-top:1px solid #e3e8ef;background:#f7f9fc}"  # noqa: E501
    ".f a{color:#3B5998;font-weight:700}"
)


def _html_embed(filas: list[FilaChartOut], actualizado: date | None) -> str:
    e = html.escape
    if filas:
        items = []
        for f in filas:
            flecha = _FLECHAS.get(f.tendencia or "")
            miniatura = (
                f'<img class="i" src="{e(f.miniatura_url, quote=True)}" alt="" loading="lazy">'
                if f.miniatura_url
                else ""
            )
            artista = f'<span class="a">{e(f.artista)}</span>' if f.artista else ""
            dir_ = f'<span class="d" style="color:{flecha[1]}">{flecha[0]}</span>' if flecha else ""
            items.append(
                f'<li><a href="{e(f.url, quote=True)}" target="_blank" rel="noopener nofollow">'
                f'<span class="n">{f.posicion}</span>{miniatura}'
                f'<span class="x"><span class="s">{e(f.titulo)}</span>{artista}</span>{dir_}</a></li>'  # noqa: E501
            )
        cuerpo = "<ol>" + "".join(items) + "</ol>"
    else:
        cuerpo = '<div class="v">La primera edición del chart se publica pronto.</div>'
    fecha = f" · edición del {actualizado.isoformat()}" if actualizado else ""
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Chart Vallenato</title>"
        f"<style>{_CSS_EMBED}</style></head><body>"
        '<h1 class="t">Chart Vallenato<small>Lo más escuchado de la semana en YouTube</small></h1>'
        f"{cuerpo}"
        f'<div class="f">Chart Vallenato · un producto de '
        f'<a href="{_URL_PAGINA_CHART}" target="_blank" rel="noopener">www.portalvallenato.com</a>'
        f"{e(fecha)}<br>Datos públicos de YouTube; las posiciones son un cálculo de "
        f'Portal Vallenato. <a href="{_URL_PRIVACIDAD}" target="_blank" rel="noopener">'
        "Política de privacidad</a></div></body></html>"
    )


@router_publico.get("/embed", response_class=HTMLResponse)
def chart_embed(
    uow: UnitOfWork = Depends(get_unit_of_work),
    n: int = Query(default=10, ge=3, le=10, description="Cuántas posiciones mostrar"),
) -> HTMLResponse:
    """The chart as a ready-made card other websites can put in an `<iframe>`.

    Shows the last published weekly edition. Server-rendered (no script),
    always carries the credit "un producto de www.portalvallenato.com" with a
    link back, the YouTube-data notice, and is the only route that
    allows being framed (see `app.api.main.add_security_headers`).
    """
    edicion = _ultima_publicada(uow)
    filas = [_fila_edicion(f) for f in edicion.filas][:n] if edicion else []
    return HTMLResponse(
        _html_embed(filas, edicion.semana_fin if edicion else None),
        headers={
            "Cache-Control": "public, max-age=900",
            "Content-Security-Policy": _CSP_EMBED,
        },
    )
