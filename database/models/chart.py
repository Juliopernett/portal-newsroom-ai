"""ORM models for the Chart Vallenato: channels, videos and daily view snapshots."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class ChartCanalModel(Base):
    """Table `chart_canales` — a YouTube channel that feeds the chart."""

    __tablename__ = "chart_canales"

    canal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    artista: Mapped[str | None] = mapped_column(String(200), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ChartVideoModel(Base):
    """Table `chart_videos` — a tracked video plus the editor's decisions."""

    __tablename__ = "chart_videos"

    video_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    canal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    artista: Mapped[str | None] = mapped_column(String(200), nullable=True)
    publicado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    miniatura_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    excluido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fijado_posicion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ChartSnapshotModel(Base):
    """Table `chart_snapshots` — total views of a video on one day."""

    __tablename__ = "chart_snapshots"

    video_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("chart_videos.video_id", ondelete="CASCADE"), primary_key=True
    )
    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    vistas: Mapped[int] = mapped_column(BigInteger, nullable=False)
