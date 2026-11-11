"""Chart Vallenato, weekly editions: "the most-played songs of the week".

Every Friday at midnight (Colombia time) the whole followed catalog is
measured once (a *close*, stored in `chart_cortes`). A week's figure is the
exact difference between two consecutive closes — never scaled, never
estimated. The edition built from it is a **draft** until the editor reviews
(exclude / pin) and publishes it.

Rules:
- A video with a close this week and one the week before ranks by the
  difference. A video published after last week's close and first seen this
  week counts from zero (it was born inside the window). Any other video
  without last week's close has no exact base: it is left out and counted in
  `sin_base`. The very first close only sets the baseline (no edition).
- Excluded videos never appear; Shorts/clips are skipped unless pinned.
- The trend compares with the **previous published** edition.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time, timedelta

from core.clock import BUSINESS_TZ
from core.entities.chart import (
    ESTADO_BORRADOR,
    ESTADO_PUBLICADA,
    CorteVistas,
    EdicionChart,
    FilaEdicion,
    VideoChart,
)
from core.ports.unit_of_work import UnitOfWork
from core.ports.youtube_reader import YouTubeError, YouTubeReader
from core.services.chart_service import aplicar_fijados

EDICION_TOP = 20
MAX_VIDEOS_POR_CANAL = 500
_LOTE_ESTADISTICAS = 50
_VIERNES = 4


class EdicionPublicadaError(RuntimeError):
    """The edition is already published and can't be regenerated."""


def semana_fin_de(ahora: datetime) -> date:
    """Colombian date of the most recent Friday whose midnight close has passed."""
    local = ahora.astimezone(BUSINESS_TZ).date()
    atras = (local.weekday() - _VIERNES) % 7 or 7
    return local - timedelta(days=atras)


def momento_corte(semana_fin: date) -> datetime:
    """The close instant of that week: Friday 24:00 Colombia = Saturday 00:00 local."""
    return datetime.combine(semana_fin + timedelta(days=1), time.min, tzinfo=BUSINESS_TZ)


def _ranking_semanal(
    videos: list[VideoChart],
    actual: dict[str, int],
    previo: dict[str, int],
    semana_fin: date,
) -> tuple[list[tuple[VideoChart, int, int, bool]], int]:
    """Return (rankable rows sorted best-first, videos left out for lack of a base)."""
    inicio_ventana = momento_corte(semana_fin - timedelta(days=7))
    filas: list[tuple[VideoChart, int, int, bool]] = []
    sin_base = 0
    for v in videos:
        if v.excluido or (v.es_short and v.fijado_posicion is None):
            continue
        total = actual.get(v.video_id)
        if total is None:
            continue
        if v.video_id in previo:
            ganadas = max(0, total - previo[v.video_id])
        elif v.publicado_en.astimezone(UTC) >= inicio_ventana.astimezone(UTC):
            ganadas = total  # born inside the window: the total is the week's figure
        else:
            sin_base += 1
            continue
        filas.append((v, ganadas, total, False))
    filas.sort(key=lambda f: (-f[1], -f[2], f[0].titulo.lower()))
    return filas, sin_base


def _tendencia(
    anterior: dict[str, int] | None, video_id: str, posicion: int
) -> tuple[str | None, int | None]:
    if anterior is None:
        return None, None
    previa = anterior.get(video_id)
    if previa is None:
        return "nuevo", None
    if previa > posicion:
        return "sube", previa
    if previa < posicion:
        return "baja", previa
    return "igual", previa


def generar_edicion(
    uow: UnitOfWork, semana_fin: date, ahora: datetime | None = None
) -> EdicionChart | None:
    """Build (or rebuild) the draft of that week from the stored closes.

    Returns None when there is no previous close at all (first measurement: it
    only sets the baseline). Raises `EdicionPublicadaError` if already published.
    """
    ahora = ahora or datetime.now(UTC)
    existente = uow.chart.get_edicion(semana_fin)
    if existente is not None and existente.estado == ESTADO_PUBLICADA:
        raise EdicionPublicadaError("Esa edición ya está publicada.")
    previo = uow.chart.list_cortes(semana_fin - timedelta(days=7))
    actual = uow.chart.list_cortes(semana_fin)
    if not previo or not actual:
        return None

    videos = uow.chart.list_videos()
    filas, sin_base = _ranking_semanal(videos, actual, previo, semana_fin)
    ordenados = aplicar_fijados(filas, videos, EDICION_TOP)

    publicada = uow.chart.ultima_publicada_antes(semana_fin)
    posiciones_previas = {f.video_id: f.posicion for f in publicada.filas} if publicada else None

    resultado = []
    for i, (v, ganadas, total, _parcial, fijado) in enumerate(ordenados, start=1):
        tendencia, previa = _tendencia(posiciones_previas, v.video_id, i)
        resultado.append(
            FilaEdicion(
                posicion=i,
                video_id=v.video_id,
                titulo=v.titulo,
                artista=v.artista,
                miniatura_url=v.miniatura_url,
                url=v.url,
                vistas_semana=ganadas,
                vistas_totales=total,
                tendencia=tendencia,
                posicion_anterior=previa,
                fijado=fijado,
            )
        )
    edicion = EdicionChart(
        semana_fin=semana_fin,
        estado=ESTADO_BORRADOR,
        filas=tuple(resultado),
        sin_base=sin_base,
        generada_en=ahora,
    )
    uow.chart.save_edicion(edicion)
    return edicion


def publicar_edicion(
    uow: UnitOfWork, semana_fin: date, ahora: datetime | None = None
) -> EdicionChart:
    """Publish a draft (idempotent for an already published one)."""
    edicion = uow.chart.get_edicion(semana_fin)
    if edicion is None:
        raise LookupError("No existe esa edición.")
    if edicion.estado == ESTADO_PUBLICADA:
        return edicion
    publicada = replace(edicion, estado=ESTADO_PUBLICADA, publicada_en=ahora or datetime.now(UTC))
    uow.chart.save_edicion(publicada)
    return publicada


@dataclass(slots=True)
class ResultadoCierre:
    semana_fin: date
    canales_ok: int = 0
    canales_con_error: list[str] = field(default_factory=list)
    videos_nuevos: int = 0
    videos_medidos: int = 0
    error_estadisticas: str | None = None
    edicion_generada: bool = False
    edicion_filas: int = 0
    sin_base: int = 0
    nota: str | None = None

    @property
    def hubo_errores(self) -> bool:
        return bool(self.canales_con_error or self.error_estadisticas)


def cerrar_semana(
    uow: UnitOfWork,
    reader: YouTubeReader,
    ahora: datetime | None = None,
    *,
    maximo_por_canal: int = MAX_VIDEOS_POR_CANAL,
) -> ResultadoCierre:
    """Weekly close: discover the whole catalog, measure it, build the draft.

    A failing channel is reported and skipped (its already-known videos are
    still measured). If the statistics call fails midway, no edition is built:
    a half-measured close would rank wrongly. Idempotent: re-running within the
    same week overwrites that week's close and draft (never a published one).
    """
    ahora = ahora or datetime.now(UTC)
    semana_fin = semana_fin_de(ahora)
    res = ResultadoCierre(semana_fin=semana_fin)

    canales = uow.chart.list_canales(solo_activos=True)
    for canal in canales:
        try:
            encontrados = reader.catalogo_canal(canal.canal_id, maximo=maximo_por_canal)
        except YouTubeError as exc:
            res.canales_con_error.append(f"{canal.nombre}: {exc}")
            continue
        res.canales_ok += 1
        for yt in encontrados:
            existente = uow.chart.get_video(yt.video_id)
            nuevo = VideoChart(
                video_id=yt.video_id,
                canal_id=yt.canal_id,
                titulo=yt.titulo,
                artista=canal.artista,
                publicado_en=yt.publicado_en,
                miniatura_url=yt.miniatura_url,
            )
            if existente is None:
                res.videos_nuevos += 1
                uow.chart.save_video(nuevo)
            else:
                uow.chart.save_video(
                    replace(
                        nuevo,
                        artista=existente.artista or canal.artista,
                        excluido=existente.excluido,
                        fijado_posicion=existente.fijado_posicion,
                        manual=existente.manual,
                        duracion_segundos=existente.duracion_segundos,
                    )
                )

    activos = {c.canal_id for c in canales}
    por_id = {v.video_id: v for v in uow.chart.list_videos() if v.manual or v.canal_id in activos}
    ids = list(por_id)
    try:
        for i in range(0, len(ids), _LOTE_ESTADISTICAS):
            for vid, d in reader.detalles(ids[i : i + _LOTE_ESTADISTICAS]).items():
                uow.chart.save_corte(
                    CorteVistas(video_id=vid, semana_fin=semana_fin, vistas=d.vistas)
                )
                res.videos_medidos += 1
                video = por_id[vid]
                if d.duracion_segundos != video.duracion_segundos:
                    uow.chart.save_video(replace(video, duracion_segundos=d.duracion_segundos))
    except YouTubeError as exc:
        res.error_estadisticas = str(exc)
        return res

    try:
        edicion = generar_edicion(uow, semana_fin, ahora)
    except EdicionPublicadaError:
        res.nota = "La edición de esta semana ya estaba publicada; no se tocó."
        return res
    if edicion is None:
        res.nota = (
            "Primer cierre: queda como línea base. La primera edición sale el próximo cierre."
        )
        return res
    res.edicion_generada = True
    res.edicion_filas = len(edicion.filas)
    res.sin_base = edicion.sin_base
    return res
