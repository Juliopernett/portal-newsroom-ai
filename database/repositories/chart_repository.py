"""SQLAlchemy adapter for `core.ports.chart_repository`."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session as SqlAlchemySession

from core.entities.chart import CanalChart, SnapshotVistas, VideoChart
from database.models.chart import ChartCanalModel, ChartSnapshotModel, ChartVideoModel


def _aware(value: datetime) -> datetime:
    """Re-attach UTC tzinfo SQLite drops on round trip (Postgres does not)."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _canal(m: ChartCanalModel) -> CanalChart:
    return CanalChart(canal_id=m.canal_id, nombre=m.nombre, artista=m.artista, activo=m.activo)


def _video(m: ChartVideoModel) -> VideoChart:
    return VideoChart(
        video_id=m.video_id,
        canal_id=m.canal_id,
        titulo=m.titulo,
        artista=m.artista,
        publicado_en=_aware(m.publicado_en),
        miniatura_url=m.miniatura_url,
        excluido=m.excluido,
        fijado_posicion=m.fijado_posicion,
        manual=m.manual,
    )


class SqlAlchemyChartRepository:
    """`ChartRepository` on top of a SQLAlchemy `Session`."""

    def __init__(self, session: SqlAlchemySession) -> None:
        self._session = session

    def save_canal(self, canal: CanalChart) -> None:
        self._session.merge(
            ChartCanalModel(
                canal_id=canal.canal_id,
                nombre=canal.nombre,
                artista=canal.artista,
                activo=canal.activo,
            )
        )

    def get_canal(self, canal_id: str) -> CanalChart | None:
        m = self._session.get(ChartCanalModel, canal_id)
        return _canal(m) if m else None

    def list_canales(self, *, solo_activos: bool = False) -> list[CanalChart]:
        stmt = select(ChartCanalModel).order_by(ChartCanalModel.nombre)
        if solo_activos:
            stmt = stmt.where(ChartCanalModel.activo.is_(True))
        return [_canal(m) for m in self._session.execute(stmt).scalars()]

    def delete_canal(self, canal_id: str) -> None:
        m = self._session.get(ChartCanalModel, canal_id)
        if m is not None:
            self._session.delete(m)

    def save_video(self, video: VideoChart) -> None:
        self._session.merge(
            ChartVideoModel(
                video_id=video.video_id,
                canal_id=video.canal_id,
                titulo=video.titulo,
                artista=video.artista,
                publicado_en=video.publicado_en,
                miniatura_url=video.miniatura_url,
                excluido=video.excluido,
                fijado_posicion=video.fijado_posicion,
                manual=video.manual,
            )
        )
        self._session.flush()

    def get_video(self, video_id: str) -> VideoChart | None:
        m = self._session.get(ChartVideoModel, video_id)
        return _video(m) if m else None

    def list_videos(self) -> list[VideoChart]:
        stmt = select(ChartVideoModel).order_by(ChartVideoModel.publicado_en.desc())
        return [_video(m) for m in self._session.execute(stmt).scalars()]

    def save_snapshot(self, snapshot: SnapshotVistas) -> None:
        self._session.merge(
            ChartSnapshotModel(
                video_id=snapshot.video_id, fecha=snapshot.fecha, vistas=snapshot.vistas
            )
        )

    def list_snapshots(
        self, video_ids: Iterable[str], *, desde: date
    ) -> dict[str, list[SnapshotVistas]]:
        ids = list(video_ids)
        resultado: dict[str, list[SnapshotVistas]] = {i: [] for i in ids}
        if not ids:
            return resultado
        stmt = (
            select(ChartSnapshotModel)
            .where(ChartSnapshotModel.video_id.in_(ids), ChartSnapshotModel.fecha >= desde)
            .order_by(ChartSnapshotModel.fecha)
        )
        for m in self._session.execute(stmt).scalars():
            resultado[m.video_id].append(SnapshotVistas(m.video_id, m.fecha, int(m.vistas)))
        return resultado
