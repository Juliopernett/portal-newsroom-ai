"""HTTP schemas for Pauta.

`PautaOut` includes the computed quota fields `core.services.pauta_service.PautaService`
already provides — no `from_attributes` shortcut here, the router builds
this explicitly since those fields don't exist on the `Pauta` entity
itself.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from core.entities.pauta import PautaTipo


class PautaCreate(BaseModel):
    """Request body for `POST /pautas`."""

    client_id: str
    fecha_inicio: date
    fecha_fin: date
    publicaciones_contratadas: int
    valor_pagado: Decimal
    fecha_pago: date
    saldo_pendiente: Decimal = Decimal("0")
    observaciones: str | None = None


class PautaOut(BaseModel):
    """Response body for a `Pauta`, including its computed quota status.

    `peso_comercial` and `tipo` are read straight from the entity
    (`core.entities.pauta.Pauta`) rather than computed here — see those
    properties' docstrings for why they live on the entity instead of
    `PautaService`.
    """

    id: str
    client_id: str
    fecha_inicio: date
    fecha_fin: date
    publicaciones_contratadas: int
    valor_pagado: Decimal
    fecha_pago: date
    saldo_pendiente: Decimal
    fecha_registro: datetime
    observaciones: str | None
    publicaciones_consumidas: int
    publicaciones_restantes: int
    vigente: bool
    vencida: bool
    cuota_agotada: bool
    peso_comercial: Decimal
    tipo: PautaTipo


class InformeLinkOut(BaseModel):
    """Response body for `POST /pautas/{pauta_id}/informe-link`."""

    url: str
    expira_en: datetime
