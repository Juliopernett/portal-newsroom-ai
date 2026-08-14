"""ORM model for Gasto.

Maps to the `gastos` table. Deliberately a separate class from
`core.entities.gasto.Gasto` — see `database/models/client.py` for why.
Translation happens in `database.repositories.gasto_repository`.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class GastoModel(Base):
    """Table `gastos` — one row per operating expense."""

    __tablename__ = "gastos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
