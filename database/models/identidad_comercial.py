"""ORM model for IdentidadComercial.

Maps to the `identidad_comercial` table — a single row, always keyed by
`core.entities.identidad_comercial.ID_UNICO`. Deliberately a separate class
from the domain entity — see `database/models/client.py` for why.
Translation happens in `database.repositories.identidad_comercial_repository`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class IdentidadComercialModel(Base):
    """Table `identidad_comercial` — one singleton row, the report's letterhead."""

    __tablename__ = "identidad_comercial"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre_comercial: Mapped[str] = mapped_column(String, nullable=False)
    razon_social: Mapped[str | None] = mapped_column(String, nullable=True)
    nit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sitio_web: Mapped[str | None] = mapped_column(String(200), nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(100), nullable=True)
    facebook: Mapped[str | None] = mapped_column(String(200), nullable=True)
    otras_redes: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_storage_key: Mapped[str | None] = mapped_column(String, nullable=True)
    logo_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
