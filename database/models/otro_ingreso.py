"""ORM model for OtroIngreso.

Maps to the `otros_ingresos` table. Deliberately a separate class from
`core.entities.otro_ingreso.OtroIngreso` — see `database/models/client.py`
for why. Translation happens in
`database.repositories.otro_ingreso_repository`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class OtroIngresoModel(Base):
    """Table `otros_ingresos` — one row per income received outside any Pauta."""

    __tablename__ = "otros_ingresos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    origen: Mapped[str] = mapped_column(String, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monto_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    fecha_cobro: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    observaciones: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
