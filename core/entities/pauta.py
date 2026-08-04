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
from enum import StrEnum
from uuid import uuid4

# Bandas de duración (en días) para inferir `Pauta.tipo` — ver esa property.
_DURACION_MAX_INDIVIDUAL = 14
_DURACION_MAX_MENSUAL = 45
_DURACION_MAX_TRIMESTRAL = 135
_DURACION_MAX_SEMESTRAL = 270


class PautaTipo(StrEnum):
    """El producto comercial que una Pauta realmente representa.

    Portal Vallenato vende dos cosas distintas bajo el mismo formulario
    ("Pauta"): publicaciones sueltas (paga por cantidad, la fecha casi no
    importa) y paquetes por tiempo (paga por vigencia, mensual/trimestral/
    semestral/anual). Ver `Pauta.tipo` para cómo se infiere cuál es cuál.
    """

    INDIVIDUAL = "individual"
    MENSUAL = "mensual"
    TRIMESTRAL = "trimestral"
    SEMESTRAL = "semestral"
    ANUAL = "anual"


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
        needed). See `tipo` below for the second property following this
        same placement rule — the pattern has now repeated once; still no
        ADR, revisit that decision if a third one shows up.

        Rounds half-up to 2 decimals explicitly — `Decimal.quantize()`
        defaults to the ambient context's rounding (`ROUND_HALF_EVEN`,
        banker's rounding), which is not the convention money is usually
        rounded with.
        """
        exacto = self.valor_pagado / self.publicaciones_contratadas
        return exacto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def tipo(self) -> PautaTipo:
        """Infer which commercial product this Pauta actually is.

        Deliberately inferred from `fecha_inicio`/`fecha_fin` alone, not a
        stored field — the user explicitly asked not to add a manual
        field, and duration is a pure function of this entity's own
        already-validated state (no collaborator needed), the same
        placement rule `peso_comercial` uses above.

        Duration, not `publicaciones_contratadas`, is the classifying
        signal — an Individual sale's date range is close to meaningless
        (bought and used same-day), while a time package's whole value
        proposition IS its date range; publication count only follows
        from that (a negotiated custom deal could pair an unusual count
        with a standard duration, but the duration still correctly says
        what kind of product was sold). Band edges are calendar months
        with slack for real-world date variance, verified against every
        historical Pauta migrated from the operator's spreadsheet:
        <15 days: Individual, <=45: Mensual, <=135: Trimestral,
        <=270: Semestral, otherwise: Anual.
        """
        duracion_dias = (self.fecha_fin - self.fecha_inicio).days
        if duracion_dias <= _DURACION_MAX_INDIVIDUAL:
            return PautaTipo.INDIVIDUAL
        if duracion_dias <= _DURACION_MAX_MENSUAL:
            return PautaTipo.MENSUAL
        if duracion_dias <= _DURACION_MAX_TRIMESTRAL:
            return PautaTipo.TRIMESTRAL
        if duracion_dias <= _DURACION_MAX_SEMESTRAL:
            return PautaTipo.SEMESTRAL
        return PautaTipo.ANUAL
