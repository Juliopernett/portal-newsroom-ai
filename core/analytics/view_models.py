"""Read-only view models returned by `AnalyticsService`.

Not domain entities (`core/entities/`) — these carry no identity or
lifecycle, they are pure computed snapshots pairing an existing entity with
a derived number. They live here, next to the service that produces them,
because nothing outside `core/analytics/` constructs them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from core.entities.client import Client
from core.entities.pauta import PautaTipo


@dataclass(frozen=True, slots=True, kw_only=True)
class ClienteIngreso:
    """A `Client` paired with their total revenue across all `Pauta`s."""

    cliente: Client
    ingresos: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientePesoComercial:
    """A `Client` paired with their aggregate `peso_comercial`.

    `peso_comercial` (see `core.entities.pauta.Pauta`) is defined per-Pauta.
    For a Client with several Pautas, this is `suma(valor_pagado) /
    suma(publicaciones_contratadas)` across all of them — the same
    totals-first math `Pauta.peso_comercial` itself uses, applied one level
    up, not an average of each Pauta's individual ratio (which would let a
    single tiny Pauta skew the result as much as a large one).
    """

    cliente: Client
    peso_comercial: Decimal


class EstadoComercial(StrEnum):
    """A one-glance read on how urgently a `Client` needs sales/account attention.

    Evaluated in priority order (see `AnalyticsService.ranking_comercial`):
    a `Client` with no vigente `Pauta` at all is `VENCIDO` regardless of
    anything else; among clients with a vigente `Pauta`, an exhausted quota
    or an imminent end date is `RENOVACION` (act now) before a merely-low
    quota is `ATENCION` (keep an eye on it); everyone else is `SALUDABLE`.
    Deliberately collapses two numbers (days left, publications left) most
    operators would otherwise have to compare by hand into one glance.
    """

    SALUDABLE = "saludable"
    ATENCION = "atencion"
    RENOVACION = "renovacion"
    VENCIDO = "vencido"


@dataclass(frozen=True, slots=True, kw_only=True)
class RankingComercialItem:
    """One row of the Ranking Comercial: a `Client`'s current contract, plus lifetime totals.

    Each `Pauta` is an independent contract in this business — quota
    left unused when one expires never carries over to the next
    (functional review, 2026-08-05: a client showing "6/32 publicaciones"
    by summing a vigente Pauta's 6 remaining together with 26 already
    dead from expired contracts implied a rolling balance that does not
    exist, and actively misled whoever was about to publish). So:

    - `tipo`, `publicaciones_contratadas`, `publicaciones_restantes` and
      `fecha_vencimiento` all describe exactly one Pauta — the client's
      *contrato de referencia* (see
      `AnalyticsService._contrato_de_referencia`): the vigente Pauta that
      started most recently, or, if none is vigente, the most recently
      started Pauta overall (so an expired client's card still has a
      concrete "last contract" to show, clearly marked `vencido` via
      `estado_comercial` rather than blank).
    - `vigente` mirrors whether that one contrato de referencia is
      vigente — equivalent to "does this client have any vigente Pauta
      at all", since the reference contract is always picked from the
      vigente ones when at least one exists.

    `valor_contratado` and `peso_comercial` are the one deliberate
    exception that *do* stay lifetime sums across every Pauta — money
    already paid does not expire the way unused publication quota does,
    so aggregating revenue is still an accurate picture, unlike quota.

    Only built for clients with at least one Pauta (see
    `AnalyticsService.ranking_comercial`) — all fields are undefined
    otherwise.
    """

    cliente: Client
    valor_contratado: Decimal
    peso_comercial: Decimal
    tipo: PautaTipo
    publicaciones_contratadas: int
    publicaciones_restantes: int
    fecha_vencimiento: date
    vigente: bool
    estado_comercial: EstadoComercial


@dataclass(frozen=True, slots=True, kw_only=True)
class RentabilidadMensualItem:
    """Ingresos, gastos y rentabilidad de un mes calendario.

    `ingresos` usa `Pauta.fecha_pago` — el mismo criterio de "dinero ya
    cobrado" que `AnalyticsService.ingresos_anio_actual`/el "Pautado este
    mes" del dashboard ya usan, no una proyección. `gastos` suma
    `Gasto.valor` cuyo `Gasto.fecha` cae en ese mes. Ver
    `core.analytics.rentabilidad_service.rentabilidad_mensual`.
    """

    anio: int
    mes: int
    ingresos: Decimal
    gastos: Decimal
    rentabilidad: Decimal
