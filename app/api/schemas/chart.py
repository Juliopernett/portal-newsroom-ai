"""HTTP schemas for the Chart Vallenato."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from core.entities.chart import MAX_POSICION_FIJADA


class FilaChartOut(BaseModel):
    posicion: int
    video_id: str
    titulo: str
    artista: str | None
    miniatura_url: str | None
    url: str
    vistas_semana: int
    vistas_totales: int
    tendencia: str | None
    posicion_anterior: int | None
    fijado: bool
    parcial: bool


class VideoSeguidoOut(BaseModel):
    """Any tracked video, ranked or not — what the editor sees to exclude/pin."""

    video_id: str
    titulo: str
    artista: str | None
    url: str
    manual: bool
    excluido: bool
    es_short: bool  # looks like a YouTube Short: kept out of the chart
    duracion_segundos: int | None
    fijado_posicion: int | None
    vistas_semana: int | None  # None = not ranked yet (less than 3 days of history)


class ChartOut(BaseModel):
    actualizado: date | None
    youtube_configurado: bool
    filas: list[FilaChartOut]
    videos: list[VideoSeguidoOut]


class FilaPublicaOut(FilaChartOut):
    """A public row: the chart row plus the artist's page on the website, if any."""

    artista_url: str | None = None


class ChartPublicoOut(BaseModel):
    """What the website's sidebar widget reads — no editor-only fields."""

    actualizado: date | None  # = semana_fin (kept for the widgets already on the site)
    semana_fin: date | None  # Colombian Friday that closed the published edition
    publicada_en: datetime | None
    filas: list[FilaPublicaOut]


class CanalIn(BaseModel):
    referencia: str = Field(min_length=2, max_length=300)
    artista: str | None = Field(default=None, max_length=200)


class CanalOut(BaseModel):
    canal_id: str
    nombre: str
    artista: str | None
    activo: bool


class VideoManualIn(BaseModel):
    referencia: str = Field(min_length=5, max_length=300)
    artista: str | None = Field(default=None, max_length=200)


class VideoPatch(BaseModel):
    excluido: bool | None = None
    fijar_en: int | None = Field(default=None, ge=1, le=MAX_POSICION_FIJADA)
    quitar_fijo: bool = False


class RecoleccionOut(BaseModel):
    canales_ok: int
    canales_con_error: list[str]
    videos_nuevos: int
    videos_seguidos: int
    snapshots: int
    error_estadisticas: str | None


class EstadoSemanalOut(BaseModel):
    semana_fin: date
    nivel: str
    mensaje: str


class FilaEdicionOut(BaseModel):
    posicion: int
    video_id: str
    titulo: str
    artista: str | None
    miniatura_url: str | None
    url: str
    vistas_semana: int
    vistas_totales: int
    tendencia: str | None
    posicion_anterior: int | None
    fijado: bool


class EdicionResumenOut(BaseModel):
    semana_fin: date
    estado: str
    filas: int
    sin_base: int
    generada_en: datetime | None
    publicada_en: datetime | None


class EdicionOut(EdicionResumenOut):
    filas_detalle: list[FilaEdicionOut]
