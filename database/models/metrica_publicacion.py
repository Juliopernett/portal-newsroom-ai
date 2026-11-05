"""ORM model for MetricaPublicacion — table `metricas_publicacion`."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class MetricaPublicacionModel(Base):
    """One row per destino: the last capture of its Meta metrics."""

    __tablename__ = "metricas_publicacion"

    destino_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("destinos_publicacion.id", ondelete="CASCADE"), primary_key=True
    )
    canal: Mapped[str] = mapped_column(String(20), nullable=False)
    alcance: Mapped[int | None] = mapped_column(nullable=True)
    vistas: Mapped[int | None] = mapped_column(nullable=True)
    reacciones: Mapped[int | None] = mapped_column(nullable=True)
    comentarios: Mapped[int | None] = mapped_column(nullable=True)
    compartidos: Mapped[int | None] = mapped_column(nullable=True)
    guardados: Mapped[int | None] = mapped_column(nullable=True)
    capturado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
