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

from core.entities.client import Client


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


@dataclass(frozen=True, slots=True, kw_only=True)
class RankingComercialItem:
    """One row of the Ranking Comercial: a `Client` aggregated across all their `Pauta`s.

    A `Client` has no single "state" in the domain when they have more
    than one `Pauta` — `fecha_vencimiento` and `vigente` are two
    deliberate, documented ways to summarize that for reporting, decided
    in Sprint 4B rather than left ambiguous:

    - `fecha_vencimiento` is the earliest `fecha_fin` among the client's
      Pautas — the soonest date that needs attention, whether it's still
      upcoming or already past.
    - `vigente` is true if at least one of the client's Pautas is vigente
      today — a client counts as having something active if any one
      contract does, not only if all of them do.

    Only built for clients with at least one Pauta (see
    `AnalyticsService.ranking_comercial`) — both fields are undefined
    otherwise.
    """

    cliente: Client
    valor_contratado: Decimal
    peso_comercial: Decimal
    publicaciones_restantes: int
    fecha_vencimiento: date
    vigente: bool
