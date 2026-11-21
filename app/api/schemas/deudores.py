"""HTTP schemas for the Deudores section (clients who owe money)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.api.schemas.client import ClientOut
from core.entities.pauta import PautaTipo


class SaldoPautaOut(BaseModel):
    pauta_id: str
    tipo: PautaTipo
    saldo_pendiente: Decimal
    fecha_pago: date
    fecha_fin: date
    dias_desde_pago: int
    vencida: bool


class DeudorOut(BaseModel):
    cliente: ClientOut
    total_pendiente: Decimal
    dias_mas_antiguo: int
    saldos: list[SaldoPautaOut]


class DeudoresOut(BaseModel):
    total_por_cobrar: Decimal
    cantidad: int
    deudores: list[DeudorOut]
