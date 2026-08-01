"""ORM model for PublicationRequest.

Maps to the `publication_requests` table. Deliberately a separate class
from `core.entities.publication_request.PublicationRequest` — see
`database/models/client.py` for why. Translation happens in
`database.repositories.publication_request_repository`.

`pauta_id` is nullable — mirrors the domain adjustment from Sprint 3B.1: a
request can exist before anyone links it to a `Pauta`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class PublicationRequestModel(Base):
    """Table `publication_requests` — one row per commercial request."""

    __tablename__ = "publication_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pauta_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pautas.id"), nullable=True, index=True
    )
    fecha_recepcion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    texto: Mapped[str] = mapped_column(String, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    prioridad_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observaciones: Mapped[str | None] = mapped_column(String, nullable=True)
