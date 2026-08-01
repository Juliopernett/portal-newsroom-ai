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
from decimal import ROUND_HALF_UP, Decimal
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

    @property
    def peso_comercial(self) -> Decimal:
        """The average revenue this Pauta generates per contracted publication.

        Deliberately a property here, not a `PautaService` method — unlike
        `esta_vigente`/`esta_vencida` (need a clock) or
        `publicaciones_consumidas`/`restantes`/`cuota_agotada` (need the
        linked `PublicationRequest` history, a different aggregate), this
        reads only `Pauta`'s own fields, needs no collaborator, and is a
        pure function of already-validated state (`publicaciones_contratadas
        > 0` is guaranteed by `__post_init__`, so no zero-division guard is
        needed). Deliberate, narrow exception to the project's usual
        data-only entities — not yet promoted to a general rule (no ADR):
        if more derived properties like this appear on other entities,
        document the principle then, not this one case in isolation.

        Rounds half-up to 2 decimals explicitly — `Decimal.quantize()`
        defaults to the ambient context's rounding (`ROUND_HALF_EVEN`,
        banker's rounding), which is not the convention money is usually
        rounded with.
        """
        exacto = self.valor_pagado / self.publicaciones_contratadas
        return exacto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
