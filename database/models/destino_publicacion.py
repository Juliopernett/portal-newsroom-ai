"""ORM model for DestinoPublicacion.

Maps to the `destinos_publicacion` table. Deliberately a separate class
from `core.entities.destino_publicacion.DestinoPublicacion` — see
`database/models/client.py` for why. Translation happens in
`database.repositories.destino_publicacion_repository`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class DestinoPublicacionModel(Base):
    """Table `destinos_publicacion` — one row per (solicitud, canal)."""

    __tablename__ = "destinos_publicacion"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    publication_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("publication_requests.id"), nullable=False, index=True
    )
    canal: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    wp_post_id: Mapped[str | None] = mapped_column(String, nullable=True)
    wp_url: Mapped[str | None] = mapped_column(String, nullable=True)
    url_publicacion: Mapped[str | None] = mapped_column(String, nullable=True)
    meta_post_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    registrado_por_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    fecha_publicacion: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultimo_error: Mapped[str | None] = mapped_column(String, nullable=True)
