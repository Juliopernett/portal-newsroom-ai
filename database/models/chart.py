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
    duracion_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ChartSnapshotModel(Base):
    """Table `chart_snapshots` — total views of a video on one day."""

    __tablename__ = "chart_snapshots"

    video_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("chart_videos.video_id", ondelete="CASCADE"), primary_key=True
    )
    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    vistas: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ChartCorteModel(Base):
    """Table `chart_cortes` — total views of a video at a weekly close."""

    __tablename__ = "chart_cortes"

    video_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("chart_videos.video_id", ondelete="CASCADE"), primary_key=True
    )
    semana_fin: Mapped[date] = mapped_column(Date, primary_key=True)
    vistas: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ChartEdicionModel(Base):
    """Table `chart_ediciones` — one weekly edition (draft or published)."""

    __tablename__ = "chart_ediciones"

    semana_fin: Mapped[date] = mapped_column(Date, primary_key=True)
    estado: Mapped[str] = mapped_column(String(16), nullable=False, default="borrador")
    sin_base: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publicada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChartEdicionFilaModel(Base):
    """Table `chart_edicion_filas` — the frozen rows of an edition."""

    __tablename__ = "chart_edicion_filas"

    semana_fin: Mapped[date] = mapped_column(
        Date, ForeignKey("chart_ediciones.semana_fin", ondelete="CASCADE"), primary_key=True
    )
    posicion: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[str] = mapped_column(String(32), nullable=False)
    titulo: Mapped[str] = mapped_column(String(300), nullable=False)
    artista: Mapped[str | None] = mapped_column(String(200), nullable=True)
    miniatura_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str] = mapped_column(String(200), nullable=False)
    vistas_semana: Mapped[int] = mapped_column(BigInteger, nullable=False)
    vistas_totales: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tendencia: Mapped[str | None] = mapped_column(String(16), nullable=True)
    posicion_anterior: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fijado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
