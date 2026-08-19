"""ORM model for PlanPauta.

Maps to the `planes_pauta` table. Deliberately a separate class from
`core.entities.plan_pauta.PlanPauta` — see `database/models/client.py` for
why. Translation happens in `database.repositories.plan_pauta_repository`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class PlanPautaModel(Base):
    """Table `planes_pauta` — one row per configurable pricing plan."""

    __tablename__ = "planes_pauta"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    cantidad_publicaciones: Mapped[int] = mapped_column(Integer, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    dias_vigencia: Mapped[int] = mapped_column(Integer, nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
