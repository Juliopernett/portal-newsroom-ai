"""Domain entities: results of a published social post, read back from Meta.

`MetricasPost` is what the platform reports for one post (value object, not
persisted). `MetricaPublicacion` is the last capture saved for one
`DestinoPublicacion` — stored so an informe never depends on Meta being
reachable when it is opened or downloaded.

Every counter is `int | None`: `None` means "Meta did not give us this
number" (missing permission, metric retired by Meta, too-old post), which
is NOT the same as zero and must never be shown or summed as zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from core.entities.destino_publicacion import CanalPublicacion

_CANALES_VALIDOS = frozenset({CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM})
_CONTADORES = ("alcance", "vistas", "reacciones", "comentarios", "compartidos", "guardados")


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricasPost:
    """Numbers Meta reports for one post; `None` = not available."""

    alcance: int | None = None
    vistas: int | None = None
    reacciones: int | None = None
    comentarios: int | None = None
    compartidos: int | None = None
    guardados: int | None = None

    def __post_init__(self) -> None:
        for nombre in _CONTADORES:
            valor = getattr(self, nombre)
            if valor is not None and valor < 0:
                raise ValueError(f"{nombre} must not be negative, got {valor!r}")

    @property
    def interacciones(self) -> int | None:
        """Reacciones + comentarios + compartidos + guardados; `None` if none is known."""
        partes = [self.reacciones, self.comentarios, self.compartidos, self.guardados]
        conocidas = [p for p in partes if p is not None]
        return sum(conocidas) if conocidas else None

    @property
    def tiene_datos(self) -> bool:
        return any(getattr(self, nombre) is not None for nombre in _CONTADORES)


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricaPublicacion:
    """The last metrics capture for one destino (Facebook/Instagram)."""

    destino_id: str
    canal: CanalPublicacion
    metricas: MetricasPost
    capturado_en: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.destino_id:
            raise ValueError("destino_id must not be empty")
        if self.canal not in _CANALES_VALIDOS:
            raise ValueError(f"canal must be facebook or instagram, got {self.canal.value!r}")
