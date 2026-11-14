"""Port for reading public data from YouTube (read-only, never uploads)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class YouTubeError(RuntimeError):
    """A YouTube request failed or the reference could not be resolved."""


@dataclass(frozen=True, slots=True, kw_only=True)
class VideoYouTube:
    video_id: str
    canal_id: str
    titulo: str
    publicado_en: datetime
    miniatura_url: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class CanalResuelto:
    canal_id: str
    nombre: str


@dataclass(frozen=True, slots=True)
class DetalleVideo:
    """Current total views and length of one video."""

    vistas: int
    duracion_segundos: int | None  # None for live streams / unknown


class YouTubeReader(Protocol):
    """Contract for the few YouTube lookups the chart needs."""

    def resolver_canal(self, referencia: str) -> CanalResuelto:
        """Resolve a channel URL, `@handle` or `UC…` id to its id and name."""
        ...

    def videos_recientes(
        self, canal_id: str, *, desde: datetime, maximo: int = 50
    ) -> list[VideoYouTube]:
        """Return the channel's uploads published on/after `desde`, newest first."""
        ...

    def catalogo_canal(self, canal_id: str, *, maximo: int = 500) -> list[VideoYouTube]:
        """Return up to `maximo` of the channel's uploads, newest first (paged)."""
        ...

    def obtener_video(self, referencia: str) -> VideoYouTube:
        """Resolve a video URL or id (for videos added by hand)."""
        ...

    def detalles(self, video_ids: list[str]) -> dict[str, DetalleVideo]:
        """Return the current views and duration per video (missing ids omitted)."""
        ...

    def videos_no_disponibles(self, video_ids: list[str]) -> set[str]:
        """Return the ids YouTube does not serve at all (deleted, private, terminated).

        A video that only hides its view count is still served, so it is not here.
        """
        ...
