"""Chart Vallenato: ranking by views gained and the daily collector.

Pure ranking (`calcular_chart`) plus an orchestrating collector
(`recolectar_chart`). The ranking only uses snapshots handed to it — it never
touches a repository or the network — so every rule below is unit-tested
without fakes beyond plain data.

Rules (agreed with the owner, 2026-11-10):
- Ranked by **views gained over the last 7 days** = latest snapshot minus the
  one from ~7 days ago. With less history (3 to 6 days) the gain is scaled up
  to 7 days and the row is flagged `parcial`; under 3 days a video is not
  ranked yet (a figure from one or two days is mostly noise).
- Excluded videos never appear. Pinned videos are forced to their position.
- The trend arrow compares with the ranking as it stood 7 days earlier; when
  there is no earlier ranking at all (the chart's first weeks) the trend is
  unknown (`None`), never claimed as "new".
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum

from core.entities.chart import SnapshotVistas, VideoChart
from core.ports.unit_of_work import UnitOfWork
from core.ports.youtube_reader import YouTubeError, YouTubeReader

DIAS_VENTANA = 7
MIN_DIAS_HISTORIAL = 3
MAX_DIAS_SNAPSHOT_VIEJO = 2  # latest snapshot must be this recent, else the video is stale
TOP_POR_DEFECTO = 10
VENTANA_DESCUBRIMIENTO_DIAS = 120
_LOTE_ESTADISTICAS = 50


class Tendencia(StrEnum):
    SUBE = "sube"
    BAJA = "baja"
    IGUAL = "igual"
    NUEVO = "nuevo"


@dataclass(frozen=True, slots=True)
class PosicionChart:
    posicion: int
    video: VideoChart
    vistas_semana: int
    vistas_totales: int
    tendencia: Tendencia | None
    posicion_anterior: int | None
    fijado: bool
    parcial: bool


_RUIDO_TITULO = re.compile(
    r"\([^)]*\)|\[[^\]]*\]|\{[^}]*\}|#\w+"
    r"|\b(?:video|videoclip|oficial|official|audio|lyric|lyrics|letra|visualizer|vevo)\b",
    re.IGNORECASE,
)


_VERSION = re.compile(r"\b(en vivo|live|remix|cover|acustic[oa]|karaoke|instrumental)\b")


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", " ", sin_tildes).strip()


def clave_cancion(video: VideoChart) -> str:
    """Same song, different upload (official channel vs VEVO, lyric video, audio…).

    Built from the artist and the title without the usual decorations. A video
    with no artist keys on its channel, so two unrelated songs that share a
    title never merge. "En vivo" versions are kept apart on purpose.
    """
    completo = _normalizar(video.titulo)
    # A live, remix or cover recording is a different version of the song.
    versiones = sorted(set(_VERSION.findall(completo)))
    titulo = _normalizar(_RUIDO_TITULO.sub(" ", video.titulo)) + "".join(f"|{x}" for x in versiones)
    quien = _normalizar(video.artista) if video.artista else f"canal:{video.canal_id}"
    return f"{quien}|{titulo}"


def deduplicar_canciones(
    filas: list[tuple[VideoChart, int, int, bool]],
) -> list[tuple[VideoChart, int, int, bool]]:
    """Keep one row per song: a pinned video first, otherwise the most viewed.

    `filas` must already be sorted best-first. The editor can still exclude or
    pin any video by hand; this only stops the same song taking two places.
    """
    vistas: set[str] = set()
    elegidas: set[str] = set()
    for v, *_ in filas:  # pinned videos claim their song first
        if v.fijado_posicion is not None:
            vistas.add(clave_cancion(v))
            elegidas.add(v.video_id)
    resultado: list[tuple[VideoChart, int, int, bool]] = []
    for fila in filas:
        v = fila[0]
        if v.video_id in elegidas:
            resultado.append(fila)
            continue
        clave = clave_cancion(v)
        if clave in vistas:
            continue
        vistas.add(clave)
        resultado.append(fila)
    return resultado


def _vistas_ganadas(
    snaps: list[SnapshotVistas], hoy: date, dias: int
) -> tuple[int, int, bool] | None:
    """Return (views gained normalized to `dias`, total views, parcial) or None."""
    validos = sorted((s for s in snaps if s.fecha <= hoy), key=lambda s: s.fecha)
    if not validos:
        return None
    ultimo = validos[-1]
    if (hoy - ultimo.fecha).days > MAX_DIAS_SNAPSHOT_VIEJO:
        return None
    base = None
    for s in validos:
        if s.fecha <= ultimo.fecha - timedelta(days=dias):
            base = s
    parcial = False
    if base is None:
        base = validos[0]
        parcial = True
    dias_reales = (ultimo.fecha - base.fecha).days
    if dias_reales < MIN_DIAS_HISTORIAL:
        return None
    ganadas = max(0, ultimo.vistas - base.vistas)
    if parcial:
        ganadas = round(ganadas * dias / dias_reales)
    return ganadas, ultimo.vistas, parcial


def _ranking_base(
    videos: list[VideoChart],
    snapshots: dict[str, list[SnapshotVistas]],
    hoy: date,
    dias: int,
) -> list[tuple[VideoChart, int, int, bool]]:
    filas: list[tuple[VideoChart, int, int, bool]] = []
    for v in videos:
        if v.excluido or (v.es_short and v.fijado_posicion is None):
            continue  # Shorts are not songs; a pin is the editor's explicit override
        r = _vistas_ganadas(snapshots.get(v.video_id, []), hoy, dias)
        if r is None:
            continue
        filas.append((v, r[0], r[1], r[2]))
    filas.sort(key=lambda f: (-f[1], -f[2], f[0].titulo.lower()))
    return deduplicar_canciones(filas)


def aplicar_fijados(
    actual: list[tuple[VideoChart, int, int, bool]], videos: list[VideoChart], top: int
) -> list[tuple[VideoChart, int, int, bool, bool]]:
    """Place pinned videos at their position and fill the rest by views gained.

    `actual` is already sorted best-first and only has rankable videos. Returns
    `(video, gained, total, parcial, fijado)` tuples, at most `top`.
    """
    datos = {f[0].video_id: f for f in actual}
    por_posicion = {
        v.fijado_posicion: v for v in videos if not v.excluido and v.fijado_posicion is not None
    }
    libres = iter(f for f in actual if f[0].fijado_posicion is None)

    ordenados: list[tuple[VideoChart, int, int, bool, bool]] = []
    posicion = 1
    while len(ordenados) < top:
        fijado = por_posicion.get(posicion)
        if fijado is not None:
            f = datos.get(fijado.video_id)
            ordenados.append(
                (fijado, f[1] if f else 0, f[2] if f else 0, f[3] if f else False, True)
            )
        else:
            siguiente = next(libres, None)
            if siguiente is None:
                if any(p > posicion for p in por_posicion):
                    posicion += 1  # keep a hole-free chart: skip ahead to the next pin
                    continue
                break
            ordenados.append((siguiente[0], siguiente[1], siguiente[2], siguiente[3], False))
        posicion += 1
    return ordenados


def calcular_chart(
    videos: list[VideoChart],
    snapshots: dict[str, list[SnapshotVistas]],
    hoy: date,
    *,
    top: int = TOP_POR_DEFECTO,
    dias: int = DIAS_VENTANA,
) -> list[PosicionChart]:
    """Return the chart for `hoy`: pinned videos in place, the rest by views gained."""
    actual = _ranking_base(videos, snapshots, hoy, dias)
    anterior = _ranking_base(videos, snapshots, hoy - timedelta(days=dias), dias)
    pos_anterior = {f[0].video_id: i + 1 for i, f in enumerate(anterior)}

    ordenados = aplicar_fijados(actual, videos, top)

    resultado: list[PosicionChart] = []
    hay_historial = bool(anterior)
    for i, (v, ganadas, total, parcial, fijado_) in enumerate(ordenados, start=1):
        previa = pos_anterior.get(v.video_id)
        tendencia: Tendencia | None
        if not hay_historial:
            tendencia = None
        elif previa is None:
            tendencia = Tendencia.NUEVO
        elif previa > i:
            tendencia = Tendencia.SUBE
        elif previa < i:
            tendencia = Tendencia.BAJA
        else:
            tendencia = Tendencia.IGUAL
        resultado.append(
            PosicionChart(
                posicion=i,
                video=v,
                vistas_semana=ganadas,
                vistas_totales=total,
                tendencia=tendencia,
                posicion_anterior=previa,
                fijado=fijado_,
                parcial=parcial,
            )
        )
    return resultado


@dataclass(slots=True)
class ResultadoRecoleccion:
    canales_ok: int = 0
    canales_con_error: list[str] = field(default_factory=list)
    videos_nuevos: int = 0
    videos_seguidos: int = 0
    snapshots: int = 0
    error_estadisticas: str | None = None


def recolectar_chart(
    uow: UnitOfWork, reader: YouTubeReader, hoy: date | None = None
) -> ResultadoRecoleccion:
    """Discover new uploads of every active channel and save today's view counts.

    Idempotent within a day (one snapshot per video per day). A failing
    channel is reported and skipped — it never aborts the rest. Editor
    decisions (`excluido`, `fijado_posicion`, `manual`) survive re-discovery.
    """
    hoy = hoy or datetime.now(UTC).date()
    desde = datetime.combine(hoy, datetime.min.time(), tzinfo=UTC) - timedelta(
        days=VENTANA_DESCUBRIMIENTO_DIAS
    )
    res = ResultadoRecoleccion()

    for canal in uow.chart.list_canales(solo_activos=True):
        try:
            encontrados = reader.videos_recientes(canal.canal_id, desde=desde)
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

    seguidos = [v for v in uow.chart.list_videos() if v.manual or _aware(v.publicado_en) >= desde]
    res.videos_seguidos = len(seguidos)
    por_id = {v.video_id: v for v in seguidos}
    ids = list(por_id)
    try:
        for i in range(0, len(ids), _LOTE_ESTADISTICAS):
            for vid, d in reader.detalles(ids[i : i + _LOTE_ESTADISTICAS]).items():
                uow.chart.save_snapshot(SnapshotVistas(video_id=vid, fecha=hoy, vistas=d.vistas))
                res.snapshots += 1
                video = por_id[vid]
                if d.duracion_segundos != video.duracion_segundos:
                    uow.chart.save_video(replace(video, duracion_segundos=d.duracion_segundos))
    except YouTubeError as exc:
        res.error_estadisticas = str(exc)
    return res


def _aware(valor: datetime) -> datetime:
    return valor if valor.tzinfo is not None else valor.replace(tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class ResultadoLimpieza:
    snapshots: int
    cortes: int
    ediciones: int


def purgar_datos_antiguos(uow: UnitOfWork, hoy: date, dias: int) -> ResultadoLimpieza:
    """Delete YouTube statistics older than `dias` days (data-retention policy).

    YouTube lets a client without approval keep API statistics for 30 days at
    most. Covers the daily snapshots, the weekly closes and the stored
    editions (whose view counts are derived from them). Idempotent.
    """
    if dias < 1:
        raise ValueError("dias must be at least 1")
    snaps, cortes, ediciones = uow.chart.purgar_anteriores_a(hoy - timedelta(days=dias))
    return ResultadoLimpieza(snapshots=snaps, cortes=cortes, ediciones=ediciones)
