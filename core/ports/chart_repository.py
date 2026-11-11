"""Port for persisting the chart's channels, videos and daily view snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Protocol

from core.entities.chart import CanalChart, CorteVistas, EdicionChart, SnapshotVistas, VideoChart


class ChartRepository(Protocol):
    def save_canal(self, canal: CanalChart) -> None: ...

    def get_canal(self, canal_id: str) -> CanalChart | None: ...

    def list_canales(self, *, solo_activos: bool = False) -> list[CanalChart]: ...

    def delete_canal(self, canal_id: str) -> None: ...

    def save_video(self, video: VideoChart) -> None:
        """Create or replace a video."""
        ...

    def get_video(self, video_id: str) -> VideoChart | None: ...

    def list_videos(self) -> list[VideoChart]: ...

    def save_snapshot(self, snapshot: SnapshotVistas) -> None:
        """Create or replace the snapshot of that video on that day."""
        ...

    def list_snapshots(
        self, video_ids: Iterable[str], *, desde: date
    ) -> dict[str, list[SnapshotVistas]]:
        """Return each video's snapshots on/after `desde`, oldest first."""
        ...

    def save_corte(self, corte: CorteVistas) -> None:
        """Create or replace the weekly-close total of that video."""
        ...

    def list_cortes(self, semana_fin: date) -> dict[str, int]:
        """Return `{video_id: views}` for the close of that week."""
        ...

    def ultimo_corte_antes(self, semana_fin: date) -> date | None:
        """Return the most recent close strictly before `semana_fin`, if any."""
        ...

    def save_edicion(self, edicion: EdicionChart) -> None:
        """Create or replace an edition together with its rows."""
        ...

    def get_edicion(self, semana_fin: date) -> EdicionChart | None: ...

    def list_ediciones(self) -> list[EdicionChart]:
        """Return every edition, newest week first (rows included)."""
        ...

    def ultima_publicada_antes(self, semana_fin: date) -> EdicionChart | None: ...

    def purgar_anteriores_a(self, fecha: date) -> tuple[int, int, int]:
        """Delete snapshots, weekly closes and editions older than `fecha`.

        Returns how many `(snapshots, cortes, ediciones)` were removed.
        """
        ...
