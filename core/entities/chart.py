"""Domain entities for the Chart Vallenato (ranking of YouTube videos).

The chart is computed from daily snapshots of each tracked video's total
view count: YouTube does not expose "views last week" for other people's
videos, so the weekly figure is a difference between two snapshots (see
`core.services.chart_service`). Nothing here talks to YouTube.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

MAX_POSICION_FIJADA = 20
# YouTube does not flag Shorts in its API. A video this short, or one titled
# with the #shorts hashtag, is treated as a Short and kept out of the chart
# (a song is never under a minute; Shorts were the noise the owner reported).
MAX_SEGUNDOS_SHORT = 60
_HASHTAG_SHORT = re.compile(r"#shorts?(?![a-z])", re.IGNORECASE)
# Clips uploaded without a real title: only a full date ("6 de noviembre de 2026"),
# or only emojis/digits/punctuation. A song always has a name made of letters.
_TITULO_SIN_NOMBRE = re.compile(
    r"^\s*\d{1,2}\s+de\s+[^\W\d_]+\s+de\s+\d{4}\s*$|^[\W\d_]*$", re.IGNORECASE
)


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
    duracion_segundos: int | None = None  # None = not known yet (or a live stream)

    def __post_init__(self) -> None:
        if not self.video_id.strip():
            raise ValueError("video_id must not be empty")
        if self.fijado_posicion is not None and not (
            1 <= self.fijado_posicion <= MAX_POSICION_FIJADA
        ):
            raise ValueError(f"fijado_posicion must be between 1 and {MAX_POSICION_FIJADA}")

    @property
    def es_short(self) -> bool:
        """Whether this is a Short or a clip rather than a song.

        True for: tagged #shorts, 60 s or less, or a title that is only a date
        or only emojis. (The name stays `es_short` for the API; it covers clips.)
        """
        if _HASHTAG_SHORT.search(self.titulo) or _TITULO_SIN_NOMBRE.match(self.titulo):
            return True
        return self.duracion_segundos is not None and self.duracion_segundos <= MAX_SEGUNDOS_SHORT

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
