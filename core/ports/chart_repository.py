"""Port for persisting the chart's channels, videos and daily view snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Protocol

from core.entities.chart import CanalChart, SnapshotVistas, VideoChart


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
