"""Domain entities for the Chart Vallenato (ranking of YouTube videos).

The chart is computed from daily snapshots of each tracked video's total
view count: YouTube does not expose "views last week" for other people's
videos, so the weekly figure is a difference between two snapshots (see
`core.services.chart_service`). Nothing here talks to YouTube.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

MAX_POSICION_FIJADA = 20


@dataclass(frozen=True, slots=True, kw_only=True)
class CanalChart:
    """A YouTube channel whose uploads feed the chart (an artist's official channel)."""

    canal_id: str
    nombre: str
    artista: str | None = None
    activo: bool = True

    def __post_init__(self) -> None:
        if not self.canal_id.strip():
            raise ValueError("canal_id must not be empty")


@dataclass(frozen=True, slots=True, kw_only=True)
class VideoChart:
    """One tracked video, plus the editor's decisions about it.

    `excluido` keeps it out of the chart (e.g. not the official song);
    `fijado_posicion` forces it to that chart position; `manual` marks a
    video added by hand rather than discovered from a channel.
    """

    video_id: str
    canal_id: str
    titulo: str
    artista: str | None = None
    publicado_en: datetime
    miniatura_url: str | None = None
    excluido: bool = False
    fijado_posicion: int | None = None
    manual: bool = False

    def __post_init__(self) -> None:
        if not self.video_id.strip():
            raise ValueError("video_id must not be empty")
        if self.fijado_posicion is not None and not (
            1 <= self.fijado_posicion <= MAX_POSICION_FIJADA
        ):
            raise ValueError(f"fijado_posicion must be between 1 and {MAX_POSICION_FIJADA}")

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


@dataclass(frozen=True, slots=True)
class SnapshotVistas:
    """Total view count of a video on one day (at most one per video per day)."""

    video_id: str
    fecha: date
    vistas: int

    def __post_init__(self) -> None:
        if self.vistas < 0:
            raise ValueError("vistas must not be negative")
