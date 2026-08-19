"""Domain entity: one row of the Pauta pricing catalog shown in Configuración.

Purely a data-entry shortcut for `PautaForm` (autocompletes
`publicaciones_contratadas`/`valor_pagado`/`fecha_fin` from `cantidad`/
`valor`/`dias_vigencia`) — never a field stored on `Pauta` itself, same
role the previously hardcoded `PLANES_CATALOGO` played before it became
editable here. `orden` controls display order in that dropdown; it is a
plain editable int, not a computed rank, so the operator can reorder
plans without recreating them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanPauta:
    """A configurable (cantidad, valor, duración) combination offered at contract time."""

    id: str = field(default_factory=lambda: str(uuid4()))
    nombre: str
    cantidad_publicaciones: int
    valor: Decimal
    dias_vigencia: int
    orden: int = 0
    fecha_registro: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise ValueError("nombre must not be empty")
        if self.cantidad_publicaciones <= 0:
            raise ValueError(
                f"cantidad_publicaciones must be positive, got {self.cantidad_publicaciones!r}"
            )
        if self.valor < 0:
            raise ValueError(f"valor must not be negative, got {self.valor!r}")
        if self.dias_vigencia <= 0:
            raise ValueError(f"dias_vigencia must be positive, got {self.dias_vigencia!r}")
