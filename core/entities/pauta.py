"""Domain entity: a purchased publication allotment for a Client.

Replaces the spreadsheet Portal Vallenato uses today to track pautas: a
number of contracted publications, valid within a date range the client
negotiates individually — never a calendar month (Sprint 3B domain
discovery). What has been consumed is never stored here — see
`core.services.pauta_service.PautaService`, which always computes it from
the linked `PublicationRequest` history, so there is never a stored number
that can drift from reality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class Pauta:
    """A commercial client's contracted publication slots for one period."""

    id: str = field(default_factory=lambda: str(uuid4()))
    client_id: str
    fecha_inicio: date
    fecha_fin: date
    publicaciones_contratadas: int
    valor_pagado: Decimal
    fecha_pago: date
    observaciones: str | None = None

    def __post_init__(self) -> None:
        if not self.client_id:
            raise ValueError("client_id must not be empty")
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("fecha_fin must be later than fecha_inicio")
        if self.publicaciones_contratadas <= 0:
            raise ValueError(
                "publicaciones_contratadas must be positive, "
                f"got {self.publicaciones_contratadas!r}"
            )
        if self.valor_pagado < 0:
            raise ValueError(f"valor_pagado must not be negative, got {self.valor_pagado!r}")
