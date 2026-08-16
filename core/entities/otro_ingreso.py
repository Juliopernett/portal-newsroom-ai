"""Domain entity: revenue that reaches Portal Vallenato outside any Pauta.

Feeds `core.analytics.rentabilidad_service.rentabilidad_mensual` on the
same side as `Pauta.valor_pagado` — both are "dinero ya cobrado" grouped
by month, just from a different origin. Meta (Facebook)/Google AdSense
payouts are the motivating case: money that lands in the bank on its own
schedule, unrelated to any client contract, but that still counts toward
the portal's real monthly income.

Deliberately flat, mirroring `core.entities.gasto.Gasto`'s own reasoning:
the real data the business tracks today is just an origen, an amount, and
a date — no recurring-payout modeling, no per-platform schema. `monto_usd`
is optional because the operator doesn't always have that figure at hand
when logging the entry; `monto` (COP) is the only value rentabilidad ever
sums, since that's what actually lands in the bank account.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class OtroIngreso:
    """Income received outside any Pauta — origen, monto, fecha de cobro.

    `fecha_registro` is an audit timestamp, the same convention
    `core.entities.gasto.Gasto.fecha_registro` established — assigned by
    the system, never client-supplied, separate from `fecha_cobro` (the
    business date the operator enters by hand).
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    origen: str
    monto: Decimal
    monto_usd: Decimal | None = None
    fecha_cobro: date
    observaciones: str | None = None
    fecha_registro: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.origen:
            raise ValueError("origen must not be empty")
        if self.monto < 0:
            raise ValueError(f"monto must not be negative, got {self.monto!r}")
        if self.monto_usd is not None and self.monto_usd < 0:
            raise ValueError(f"monto_usd must not be negative, got {self.monto_usd!r}")
        if self.observaciones == "":
            raise ValueError(
                "observaciones must not be an empty string — use None if not set"
            )
