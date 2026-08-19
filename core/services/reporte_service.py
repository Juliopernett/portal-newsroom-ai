"""Domain service: build a PublicationRequest's report.

Sprint 4A, Incremento 6 (see docs/adr/ADR-006-multichannel-publication.md
— "Reportes automáticos para clientes"). `construir_reporte` is a pure
function: it never touches a repository or the network, it only shapes
data already handed to it — the same "compute, don't fetch" discipline
`core.analytics.analytics_service.AnalyticsService` already follows.
Generación automática (el reporte se arma solo, en el momento en que se
pide), envío manual (compartirlo con el cliente sigue siendo una acción
humana — ver la decisión del usuario, Sprint 4A, "Reportes automáticos
para clientes: generación automática, envío manual").
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from core.entities.client import Client
from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest
from core.services.destino_publicacion_service import esta_completa
from core.services.pauta_service import PautaService


@dataclass(frozen=True, slots=True, kw_only=True)
class ReporteDestino:
    """One destino's row in a PublicationRequest's report."""

    canal: CanalPublicacion
    estado: EstadoDestino
    enlace: str | None
    fecha_publicacion: datetime | None
    ultimo_error: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ReporteSolicitud:
    """The report for one PublicationRequest: enlaces, fechas, estado, pauta consumida.

    `completa` and `pauta_consumida` are deliberately separate: a
    solicitud can be `completa` (`esta_completa` over its own destinos)
    without ever having a `Pauta` linked (e.g. an Instagram-only request
    confirmed directly on a still-RECIBIDA solicitud, see ADR-006) — that
    case is complete but consumes no quota, since there is no Pauta to
    consume it from.
    """

    publication_request_id: str
    titulo: str | None
    texto: str
    cliente_nombre: str | None
    pauta_id: str | None
    fecha_recepcion: datetime
    fecha_cierre: datetime | None
    completa: bool
    pauta_consumida: bool
    destinos: tuple[ReporteDestino, ...]


def _enlace_de(destino: DestinoPublicacion) -> str | None:
    """Return the one link that matters for `destino`'s canal.

    Same rule the frontend already applies per destino row — centralized
    here so there is exactly one place that knows `wp_url` is WordPress's
    link and `url_publicacion` is everyone else's.
    """
    return (
        destino.wp_url if destino.canal == CanalPublicacion.WORDPRESS else destino.url_publicacion
    )


def construir_reporte(
    solicitud: PublicationRequest,
    destinos: Sequence[DestinoPublicacion],
    cliente: Client | None,
) -> ReporteSolicitud:
    """Build `solicitud`'s report from its own destinos and (optional) Client.

    `cliente` is `None` when `solicitud.pauta_id` is `None`, or when the
    caller chooses not to resolve it — `cliente_nombre` simply comes back
    `None` in that case, the report still builds.
    """
    completa = esta_completa(destinos)
    return ReporteSolicitud(
        publication_request_id=solicitud.id,
        titulo=solicitud.titulo,
        texto=solicitud.texto,
        cliente_nombre=cliente.nombre if cliente is not None else None,
        pauta_id=solicitud.pauta_id,
        fecha_recepcion=solicitud.fecha_recepcion,
        fecha_cierre=solicitud.fecha_cierre,
        completa=completa,
        pauta_consumida=completa and solicitud.pauta_id is not None,
        destinos=tuple(
            ReporteDestino(
                canal=destino.canal,
                estado=destino.estado,
                enlace=_enlace_de(destino),
                fecha_publicacion=destino.fecha_publicacion,
                ultimo_error=destino.ultimo_error,
            )
            for destino in destinos
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportePauta:
    """The report for one Pauta (contrato): resumen ejecutivo + solicitudes consumidas.

    `publicaciones_consumidas`/`restantes` and `vigente`/`vencida` are
    never recomputed here — they come straight from `PautaService`, the
    one place this codebase is allowed to answer those questions (see
    `core.services.pauta_service`). `solicitudes` holds only the ones
    `pauta_consumida` (Sprint — informe de cierre de contrato): a Pauta
    with requests still pending or never linked shows none of those here,
    same as `publicaciones_consumidas` not counting them.
    """

    pauta: Pauta
    cliente_nombre: str | None
    publicaciones_consumidas: int
    publicaciones_restantes: int
    vigente: bool
    vencida: bool
    cuota_agotada: bool
    canales_utilizados: tuple[CanalPublicacion, ...]
    fecha_primera_publicacion: datetime | None
    fecha_ultima_publicacion: datetime | None
    solicitudes: tuple[ReporteSolicitud, ...]


def construir_reporte_pauta(
    pauta: Pauta,
    solicitudes: Sequence[PublicationRequest],
    destinos: Sequence[DestinoPublicacion],
    cliente: Client | None,
    pauta_service: PautaService,
) -> ReportePauta:
    """Build `pauta`'s closing report from its own solicitudes/destinos history.

    `solicitudes`/`destinos` may span more than one Pauta (the same shape
    `PautaService`'s own methods accept) — this filters to `pauta.id`
    internally, so a caller can pass exactly what
    `uow.publication_requests.list_by_pauta_id`/
    `uow.destinos_publicacion.list_by_publication_request_id` already
    return without pre-filtering itself.

    Every `ReporteSolicitud` here is built by `construir_reporte`, the same
    function `GET /publication-requests/{id}/reporte` already uses — no
    second way of deciding "what counts as a publicación", by construction
    (see the module docstring's "compute, don't fetch" discipline).
    """
    destinos_por_solicitud: dict[str, list[DestinoPublicacion]] = {}
    for destino in destinos:
        destinos_por_solicitud.setdefault(destino.publication_request_id, []).append(destino)

    solicitudes_de_pauta = [s for s in solicitudes if s.pauta_id == pauta.id]
    reportes_solicitud = [
        construir_reporte(s, destinos_por_solicitud.get(s.id, []), cliente)
        for s in solicitudes_de_pauta
    ]
    consumidas = tuple(
        sorted(
            (r for r in reportes_solicitud if r.pauta_consumida),
            key=lambda r: r.fecha_cierre or r.fecha_recepcion,
        )
    )

    canales: set[CanalPublicacion] = set()
    fechas_publicacion: list[datetime] = []
    for reporte_solicitud in consumidas:
        for reporte_destino in reporte_solicitud.destinos:
            if reporte_destino.estado == EstadoDestino.PUBLICADO:
                canales.add(reporte_destino.canal)
                if reporte_destino.fecha_publicacion is not None:
                    fechas_publicacion.append(reporte_destino.fecha_publicacion)

    return ReportePauta(
        pauta=pauta,
        cliente_nombre=cliente.nombre if cliente is not None else None,
        publicaciones_consumidas=pauta_service.publicaciones_consumidas(
            pauta, solicitudes, destinos
        ),
        publicaciones_restantes=pauta_service.publicaciones_restantes(pauta, solicitudes, destinos),
        vigente=pauta_service.esta_vigente(pauta),
        vencida=pauta_service.esta_vencida(pauta),
        cuota_agotada=pauta_service.cuota_agotada(pauta, solicitudes, destinos),
        canales_utilizados=tuple(sorted(canales, key=lambda canal: canal.value)),
        fecha_primera_publicacion=min(fechas_publicacion) if fechas_publicacion else None,
        fecha_ultima_publicacion=max(fechas_publicacion) if fechas_publicacion else None,
        solicitudes=consumidas,
    )
