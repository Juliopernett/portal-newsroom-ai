"""ORM model for ColoresMarca (table `colores_marca`, one singleton row)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class ColoresMarcaModel(Base):
    """Table `colores_marca` — the colours of the generated images."""

    __tablename__ = "colores_marca"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fondo: Mapped[str] = mapped_column(String(7), nullable=False)
    destacado: Mapped[str] = mapped_column(String(7), nullable=False)
    texto_destacado: Mapped[str] = mapped_column(String(7), nullable=False)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
