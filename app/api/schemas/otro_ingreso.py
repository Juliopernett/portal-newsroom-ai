"""HTTP schemas for OtroIngreso."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OtroIngresoCreate(BaseModel):
    """Request body for `POST /otros-ingresos` and `PUT /otros-ingresos/{id}`."""

    origen: str
    monto: Decimal
    monto_usd: Decimal | None = None
    fecha_cobro: date
    observaciones: str | None = None


class OtroIngresoOut(BaseModel):
    """Response body for an `OtroIngreso`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    origen: str
    monto: Decimal
    monto_usd: Decimal | None
    fecha_cobro: date
    observaciones: str | None
    fecha_registro: datetime
