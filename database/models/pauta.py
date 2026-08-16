"""ORM model for Pauta.

Maps to the `pautas` table. Deliberately a separate class from
`core.entities.pauta.Pauta` — see `database/models/client.py` for why.
Translation happens in `database.repositories.pauta_repository`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class PautaModel(Base):
    """Table `pautas` — one row per contracted publication allotment."""

    __tablename__ = "pautas"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=False, index=True
    )
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    publicaciones_contratadas: Mapped[int] = mapped_column(nullable=False)
    valor_pagado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    saldo_pendiente: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(String, nullable=True)
