"""Domain entity: the colours of every image the app generates.

News covers and the weekly Radar Vallenato cards share them, so the pieces
posted on social networks look like portalvallenato.com. A singleton, like
`IdentidadComercial`; while nobody saves one, the website's own colours apply.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

ID_UNICO: Final = "colores-marca"
_HEX = re.compile(r"#[0-9A-F]{6}")


@dataclass(frozen=True, slots=True, kw_only=True)
class ColoresMarca:
    """Three colours as `#RRGGBB`; the defaults are the website's."""

    id: str = ID_UNICO
    fondo: str = "#3B5998"  # the website's menu blue
    destacado: str = "#E1CE26"  # the website's yellow
    texto_destacado: str = "#083A7A"  # lettering on top of `destacado`
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        for nombre in ("fondo", "destacado", "texto_destacado"):
            valor = getattr(self, nombre).strip().upper()
            if not _HEX.fullmatch(valor):
                raise ValueError(f"{nombre} must be a colour like #3B5998, got {valor!r}")
            object.__setattr__(self, nombre, valor)
