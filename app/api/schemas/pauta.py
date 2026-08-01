"""HTTP schemas for Pauta.

`PautaOut` includes the computed quota fields `core.services.pauta_service.PautaService`
already provides — no `from_attributes` shortcut here, the router builds
this explicitly since those fields don't exist on the `Pauta` entity
itself.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class PautaCreate(BaseModel):
    """Request body for `POST /pautas`."""

    client_id: str
    fecha_inicio: date
    fecha_fin: date
    publicaciones_contratadas: int
    valor_pagado: Decimal
    fecha_pago: date
    observaciones: str | None = None


class PautaOut(BaseModel):
    """Response body for a `Pauta`, including its computed quota status."""

    id: str
    client_id: str
    fecha_inicio: date
    fecha_fin: date
    publicaciones_contratadas: int
    valor_pagado: Decimal
    fecha_pago: date
    observaciones: str | None
    publicaciones_consumidas: int
    publicaciones_restantes: int
    vigente: bool
    vencida: bool
    cuota_agotada: bool
