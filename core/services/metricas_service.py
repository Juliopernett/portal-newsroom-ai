"""Pure aggregation of social-media metrics for one Pauta's informe.

Handed already-loaded data, never touches a repository or the network —
same discipline as `core.services.reporte_service`. A counter Meta did not
provide (`None`) is skipped, never summed as zero, so a total only ever
claims what was actually measured.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.entities.destino_publicacion import CanalPublicacion
from core.entities.metrica_publicacion import MetricaPublicacion


@dataclass(frozen=True, slots=True, kw_only=True)
class FilaMetrica:
    """One published Facebook/Instagram post of a Pauta, with its last capture."""

    destino_id: str
    solicitud_id: str
    titulo: str
    canal: CanalPublicacion
    url: str | None
    tiene_meta_post_id: bool
    metrica: MetricaPublicacion | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ResumenMetricas:
    """Totals over the posts that have data; `None` when no post measured it."""

    publicaciones_total: int
    publicaciones_con_datos: int
    publicaciones_sin_datos: int
    alcance_total: int | None
    vistas_total: int | None
    interacciones_total: int | None


def _sumar(valores: list[int | None]) -> int | None:
    conocidos = [v for v in valores if v is not None]
    return sum(conocidos) if conocidos else None


def resumir(filas: list[FilaMetrica]) -> ResumenMetricas:
    """Aggregate `filas`; posts without a capture count as "sin datos"."""
    con_datos = [f for f in filas if f.metrica is not None and f.metrica.metricas.tiene_datos]
    return ResumenMetricas(
        publicaciones_total=len(filas),
        publicaciones_con_datos=len(con_datos),
        publicaciones_sin_datos=len(filas) - len(con_datos),
        alcance_total=_sumar([f.metrica.metricas.alcance for f in con_datos if f.metrica]),
        vistas_total=_sumar([f.metrica.metricas.vistas for f in con_datos if f.metrica]),
        interacciones_total=_sumar(
            [f.metrica.metricas.interacciones for f in con_datos if f.metrica]
        ),
    )
