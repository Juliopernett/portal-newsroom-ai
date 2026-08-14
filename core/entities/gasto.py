"""Domain entity: one operating expense of Portal Vallenato.

Feeds the monthly profitability report (`core.analytics.rentabilidad_service`)
on the other side of `Pauta.valor_pagado` — revenue in, cost out. Deliberately
flat (no categoria/recurrencia) because the real data the business tracks
today (a WhatsApp/Excel list of "PAGOS") is just a description, an amount,
and a date; adding a taxonomy nobody asked for would be speculative, not
requested.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class Gasto:
    """An operating expense — descripción, valor pagado, fecha del gasto.

    `fecha_registro` is an audit timestamp, the same convention
    `core.entities.pauta.Pauta.fecha_registro` established — assigned by
    the system, never client-supplied, separate from `fecha` (the business
    date the operator enters by hand).
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    descripcion: str
    valor: Decimal
    fecha: date
    fecha_registro: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.descripcion:
            raise ValueError("descripcion must not be empty")
        if self.valor < 0:
            raise ValueError(f"valor must not be negative, got {self.valor!r}")
