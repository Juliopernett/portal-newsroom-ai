"""HTTP schemas for Gasto."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class GastoCreate(BaseModel):
    """Request body for `POST /gastos` and `PUT /gastos/{id}`."""

    descripcion: str
    valor: Decimal
    fecha: date


class GastoOut(BaseModel):
    """Response body for a `Gasto`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    descripcion: str
    valor: Decimal
    fecha: date
    fecha_registro: datetime
