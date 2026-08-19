"""HTTP schemas for PlanPauta."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PlanPautaCreate(BaseModel):
    """Request body for `POST /planes-pauta` and `PUT /planes-pauta/{id}`."""

    nombre: str
    cantidad_publicaciones: int
    valor: Decimal
    dias_vigencia: int
    orden: int = 0


class PlanPautaOut(BaseModel):
    """Response body for a `PlanPauta`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    cantidad_publicaciones: int
    valor: Decimal
    dias_vigencia: int
    orden: int
    fecha_registro: datetime
