"""Domain service: read-only business metrics over the Commercial pillar.

`AnalyticsService` answers the reporting questions Portal Vallenato has no
way to answer today short of counting rows in a spreadsheet by hand: how
many clients are active, how much revenue is at risk, which pautas need
attention. It never touches FastAPI, HTML, a template engine or any other
delivery concern — those are for whatever calls this (a future dashboard
route, a PDF export, an automation) to build on top of what this returns.

Deliberately bound to one `clients`/`pautas`/`solicitudes` snapshot at
construction rather than accepting them per method (contrast
`core.services.pauta_service.PautaService`, which is stateless and takes
its data per call): every metric here is meant to be read from the same
fetch, so a caller computing several of these can't accidentally mix an
older `pautas` list with a newer `clients` one. Still has zero side
effects — nothing here ever mutates its inputs, persists anything, or
reaches out to any repository itself.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from core.analytics.view_models import (
    ClienteIngreso,
    ClientePesoComercial,
    EstadoComercial,
    RankingComercialItem,
)
from core.clock import now_local
from core.entities.client import Client
from core.entities.pauta import Pauta, PautaTipo
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.services.pauta_service import PautaService

_CUPO_BAJO_UMBRAL = Decimal("0.2")
_PAQUETES_PREMIUM = frozenset({PautaTipo.SEMESTRAL, PautaTipo.ANUAL})

# Umbrales de core.analytics.view_models.EstadoComercial — ver ese docstring.
_RENOVACION_DIAS = 7
_ATENCION_RESTANTES = 5


class AnalyticsService:
    """Computes business metrics from a fixed snapshot of domain data."""

    def __init__(
        self,
        clients: Sequence[Client],
        pautas: Sequence[Pauta],
        solicitudes: Sequence[PublicationRequest],
        clock: Callable[[], datetime] = lambda: now_local(),
    ) -> None:
        """`clock` is injectable so tests can control what "now" means.

        Feeds one `PautaService` internally, built from the same `clock` (as
        a date), rather than accepting an external `PautaService` — a
        single knob for "now" instead of two independently-injectable
        clocks that could disagree in tests.
        """
        self._clients = clients
        self._pautas = pautas
        self._solicitudes = solicitudes
        self._clock = clock
        self._pauta_service = PautaService(clock=lambda: clock().date())

    # ---------- Dashboard Ejecutivo ----------

    def cantidad_clientes(self) -> int:
        """Return how many `Client`s exist, active or not."""
        return len(self._clients)

    def cantidad_clientes_activos(self) -> int:
        """Return how many `Client`s have at least one currently-vigente `Pauta`.

        "Cliente activo" is not a stored field on `Client` — there is no
        status flag. Defined here as "has a `Pauta` that
        `PautaService.esta_vigente` says is valid today", the only
        definition derivable from existing data.
        """
        activos = {
            pauta.client_id for pauta in self._pautas if self._pauta_service.esta_vigente(pauta)
        }
        return len(activos)

    def cantidad_pautas_vigentes(self) -> int:
        """Return how many `Pauta`s are within their contracted date range today."""
        return len(self.pautas_activas())

    def cantidad_pautas_vencidas(self) -> int:
        """Return how many `Pauta`s have already passed their end date."""
        return len(self.pautas_vencidas())

    def cantidad_publicaciones_pendientes(self) -> int:
        """Return how many `PublicationRequest`s are still `RECIBIDA`."""
        return len(self.solicitudes_pendientes())

    def cantidad_publicaciones_publicadas(self) -> int:
        """Return how many `PublicationRequest`s have been `PUBLICADA`."""
        return len(self.solicitudes_publicadas())

    def ingresos_anio_actual(self) -> Decimal:
        """Return total `valor_pagado` across every `Pauta` started in the current year.

        Uses `fecha_inicio` as the revenue-recognition date — migrated
        records have no separate "date received" field, so `fecha_inicio`
        is the closest proxy for "when this revenue counts". Includes
        vigente, vencida, and future `Pauta`s alike; only the year of
        `fecha_inicio` matters, not whether the contract is active today.
        """
        anio_actual = self._clock().year
        return sum(
            (p.valor_pagado for p in self._pautas if p.fecha_inicio.year == anio_actual),
            start=Decimal("0"),
        )

    def ingresos_historicos(self) -> Decimal:
        """Return total `valor_pagado` across every `Pauta`, past or present."""
        return sum((p.valor_pagado for p in self._pautas), start=Decimal("0"))

    def cantidad_publicaciones_publicadas_este_mes(self) -> int:
        """Return how many `PublicationRequest`s were published in the current month.

        `PublicationRequest` has no separate "fecha_publicacion" — only
        `fecha_recepcion` (when it arrived). Sprint 4B (dashboard) needs
        "this month" and the domain has no better date to use, so this
        reads `fecha_recepcion` on the already-`PUBLICADA` requests. For
        historical, migrated data this reflects when the request was
        logged as received, not necessarily the exact publish date — a
        known limitation, not something this sprint's scope covers fixing
        (would need a new field on `PublicationRequest`).
        """
        ahora = self._clock()
        return sum(
            1
            for s in self.solicitudes_publicadas()
            if s.fecha_recepcion.year == ahora.year and s.fecha_recepcion.month == ahora.month
        )

    def peso_comercial_promedio(self) -> Decimal:
        """Return the average `peso_comercial` across clients that have one.

        Reuses `ranking_clientes_por_peso_comercial` rather than
        recomputing — an arithmetic mean of each client's already
        totals-first aggregate, not a second independent calculation.
        Zero with no ranked clients, avoiding a division by zero.
        """
        ranking = self.ranking_clientes_por_peso_comercial()
        if not ranking:
            return Decimal("0")
        total = sum((item.peso_comercial for item in ranking), start=Decimal("0"))
        return (total / len(ranking)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ---------- Reportes Comerciales ----------

    def ranking_clientes_por_ingresos(self) -> list[ClienteIngreso]:
        """Return every `Client` with their total revenue, highest first."""
        ranking = [
            ClienteIngreso(cliente=cliente, ingresos=self._ingresos_de(cliente.id))
            for cliente in self._clients
        ]
        ranking.sort(key=lambda item: item.ingresos, reverse=True)
        return ranking

    def ranking_clientes_por_peso_comercial(self) -> list[ClientePesoComercial]:
        """Return `Client`s with at least one `Pauta`, ranked by aggregate peso_comercial.

        Clients with no `Pauta` are excluded — see `ClientePesoComercial`'s
        docstring for why this is a totals-first aggregate, not an average
        of each Pauta's individual ratio.
        """
        ranking = []
        for cliente in self._clients:
            pautas_cliente = self._pautas_de(cliente.id)
            if not pautas_cliente:
                continue
            total_pagado = sum((p.valor_pagado for p in pautas_cliente), start=Decimal("0"))
            total_contratadas = sum(p.publicaciones_contratadas for p in pautas_cliente)
            peso = (total_pagado / total_contratadas).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            ranking.append(ClientePesoComercial(cliente=cliente, peso_comercial=peso))
        ranking.sort(key=lambda item: item.peso_comercial, reverse=True)
        return ranking

    def clientes_por_vencer(self, dias: int = 7) -> list[Client]:
        """Return `Client`s with a `Pauta` expiring within `dias` days."""
        client_ids = {pauta.client_id for pauta in self.pautas_por_vencer(dias)}
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def clientes_con_cupo_agotado(self) -> list[Client]:
        """Return `Client`s with a currently-vigente `Pauta` whose quota is exhausted.

        Only vigente Pautas count (Sprint 4C functional review) — a
        vencida Pauta is closed history, not something the team needs to
        act on today, regardless of how much quota it left unused. See
        `clientes_con_publicaciones_sin_usar` for that historical question,
        deliberately kept separate. `pautas_agotadas` itself is untouched —
        it stays the complete historical list, vigente or not.
        """
        client_ids = {
            pauta.client_id
            for pauta in self.pautas_agotadas()
            if self._pauta_service.esta_vigente(pauta)
        }
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def clientes_con_cupo_bajo(self) -> list[Client]:
        """Return `Client`s with a currently-vigente `Pauta` at under 20% of its quota remaining.

        Only vigente Pautas count (Sprint 4C functional review, same
        reasoning as `clientes_con_cupo_agotado`). A business threshold,
        distinct from the presentation-only `LOW_QUOTA_THRESHOLD` (an
        absolute count of 2) in `app.js`, used only to decide what gets a
        warning badge on screen. The two are not required to agree — this
        one is a percentage of what was contracted, that one is a fixed
        headcount, and they serve different readers.
        """
        client_ids = {
            pauta.client_id
            for pauta in self._pautas
            if self._pauta_service.esta_vigente(pauta) and self._tiene_cupo_bajo(pauta)
        }
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def clientes_con_menos_de_n_publicaciones_restantes(self, minimo: int = 3) -> list[Client]:
        """Return `Client`s with a vigente `Pauta` at fewer than `minimo` publications remaining.

        An absolute-count threshold, deliberately separate from
        `clientes_con_cupo_bajo` (a 20% threshold) — Sprint 4B asked for
        this exact reading ("menos de 3 publicaciones restantes"), not a
        restatement of the percentage-based one. Both coexist; they serve
        different questions ("how close to zero" vs. "what fraction is
        left"). Only vigente Pautas count (Sprint 4C functional review) —
        a client whose only low-quota Pauta already expired isn't an
        actionable "about to run out" alert, it's closed history; without
        this filter the widget answered "which clients ever left
        publications unused" instead of "which active clients need
        follow-up now", which is what it was actually meant to answer.
        """
        client_ids = {
            pauta.client_id
            for pauta in self._pautas
            if self._pauta_service.esta_vigente(pauta)
            and self._pauta_service.publicaciones_restantes(pauta, self._solicitudes) < minimo
        }
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def clientes_con_publicaciones_individuales_pendientes(self) -> list[Client]:
        """Return `Client`s with a vigente `PautaTipo.INDIVIDUAL` Pauta that still has quota left.

        Individual purchases (see `Pauta.tipo`) don't expire in any
        meaningful sense — the date range is close to a formality — so
        this is framed around "still has unpublished posts", not a
        deadline.
        """
        client_ids = {
            pauta.client_id
            for pauta in self._pautas
            if pauta.tipo is PautaTipo.INDIVIDUAL
            and self._pauta_service.esta_vigente(pauta)
            and self._pauta_service.publicaciones_restantes(pauta, self._solicitudes) > 0
        }
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def clientes_con_contrato_por_renovar(self, dias: int = 7) -> list[Client]:
        """Return `Client`s with a time-package Pauta (not Individual) expiring within `dias` days.

        "Renovar" only makes sense for a time package (mensual/
        trimestral/semestral/anual, see `Pauta.tipo`) — an Individual
        purchase isn't renewed, the client just buys another batch, so it
        is excluded here even though it would otherwise qualify via
        `pautas_por_vencer`.
        """
        client_ids = {
            pauta.client_id
            for pauta in self.pautas_por_vencer(dias)
            if pauta.tipo is not PautaTipo.INDIVIDUAL
        }
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def clientes_con_publicaciones_sin_usar(self) -> list[Client]:
        """Return `Client`s with an already-vencida Pauta that still had quota left when it expired.

        The mirror image of `clientes_con_menos_de_n_publicaciones_restantes`
        and `clientes_con_cupo_bajo`: those two deliberately look only at
        vigente Pautas (an operational "who needs follow-up now" question).
        This one deliberately looks only at vencida ones — a sales/history
        report ("who left money on the table"), not an action item, kept
        as its own report instead of being mixed into the operational
        alerts.
        """
        client_ids = {
            pauta.client_id
            for pauta in self._pautas
            if self._pauta_service.esta_vencida(pauta)
            and self._pauta_service.publicaciones_restantes(pauta, self._solicitudes) > 0
        }
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def valor_promedio_por_cliente(self) -> Decimal:
        """Return the average total revenue per `Client` (`ingresos_historicos` / client count).

        Zero with no clients, avoiding a division by zero.
        """
        if not self._clients:
            return Decimal("0")
        return (self.ingresos_historicos() / len(self._clients)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def clientes_premium(self) -> list[Client]:
        """Return `Client`s with a vigente Semestral or Anual `Pauta`.

        "Premium" here means the highest-commitment package tiers (see
        `Pauta.tipo`), not a revenue threshold — a client could spend a
        lot across many small Individual purchases without ever being
        "Premium" in this sense, which is exactly the distinction the
        user asked this to capture.
        """
        client_ids = {
            pauta.client_id
            for pauta in self._pautas
            if self._pauta_service.esta_vigente(pauta) and pauta.tipo in _PAQUETES_PREMIUM
        }
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def ranking_comercial(self) -> list[RankingComercialItem]:
        """Return the Ranking Comercial: one row per `Client` with at least one `Pauta`.

        `publicaciones_contratadas`/`publicaciones_restantes`/`fecha_vencimiento`
        describe the client's *contrato de referencia* only (see
        `_contrato_de_referencia`) — never a sum across every Pauta the
        client has ever had. Each Pauta is an independent contract in
        this business: quota left on an expired one does not carry over
        to the next (functional review, 2026-08-05 — a "6/32" balance
        that summed a vigente Pauta's 6 remaining with 26 already-dead
        ones implied publications pile up across contracts, which is
        false and actively misleading for someone about to publish).
        `valor_contratado`/`peso_comercial` stay lifetime sums — money
        already paid doesn't expire the way unused quota does, so
        aggregating those is still accurate.

        Built from `ranking_clientes_por_ingresos` and
        `ranking_clientes_por_peso_comercial` — no revenue or
        peso_comercial math is repeated here. Already sorted by
        `peso_comercial` descending, inherited from
        `ranking_clientes_por_peso_comercial`'s own order.
        """
        ingresos_por_cliente = {
            item.cliente.id: item.ingresos for item in self.ranking_clientes_por_ingresos()
        }
        ranking = []
        for peso_item in self.ranking_clientes_por_peso_comercial():
            pautas_cliente = self._pautas_de(peso_item.cliente.id)
            contrato = self._contrato_de_referencia(pautas_cliente)
            restantes = self._pauta_service.publicaciones_restantes(contrato, self._solicitudes)
            ranking.append(
                RankingComercialItem(
                    cliente=peso_item.cliente,
                    valor_contratado=ingresos_por_cliente[peso_item.cliente.id],
                    peso_comercial=peso_item.peso_comercial,
                    tipo=contrato.tipo,
                    publicaciones_contratadas=contrato.publicaciones_contratadas,
                    publicaciones_restantes=restantes,
                    fecha_vencimiento=contrato.fecha_fin,
                    vigente=self._pauta_service.esta_vigente(contrato),
                    estado_comercial=self._estado_comercial(pautas_cliente),
                )
            )
        return ranking

    # ---------- Reportes de Pautas ----------

    def pautas_activas(self) -> list[Pauta]:
        """Return every `Pauta` within its contracted date range today."""
        return [p for p in self._pautas if self._pauta_service.esta_vigente(p)]

    def pautas_vencidas(self) -> list[Pauta]:
        """Return every `Pauta` whose end date has already passed."""
        return [p for p in self._pautas if self._pauta_service.esta_vencida(p)]

    def pautas_por_vencer(self, dias: int = 7) -> list[Pauta]:
        """Return every `Pauta` expiring within `dias` days.

        A thin delegate to `PautaService.pautas_por_vencer` — that
        computation already exists in the domain, this does not
        reimplement it.
        """
        return self._pauta_service.pautas_por_vencer(self._pautas, dentro_de_dias=dias)

    def pautas_agotadas(self) -> list[Pauta]:
        """Return every `Pauta` with no contracted publications left."""
        return [p for p in self._pautas if self._pauta_service.cuota_agotada(p, self._solicitudes)]

    # ---------- Reportes Editoriales ----------

    def solicitudes_pendientes(self) -> list[PublicationRequest]:
        """Return every `PublicationRequest` still awaiting triage (`RECIBIDA`)."""
        return [s for s in self._solicitudes if s.estado == PublicationRequestStatus.RECIBIDA]

    def solicitudes_pendientes_priorizadas(self) -> list[PublicationRequest]:
        """Return `solicitudes_pendientes` in the order the editorial team should work them.

        Prioridad manual > peso comercial de la Pauta asociada (mayor
        primero) > fecha de recepción (la más antigua primero) — una
        regla de negocio explícita (2026-08-05): la cola no debe
        depender solo de cuándo llegó cada solicitud, debe reflejar qué
        cliente genera más ingreso para Portal Vallenato, sin que eso
        nunca le gane a una prioridad manual puesta a mano.

        Una solicitud sin Pauta vinculada todavía (`pauta_id is None`)
        cuenta como peso comercial 0 — el valor más bajo posible, así
        nunca compite injustamente con una ya vinculada a un cliente
        real; sigue pudiendo saltar al frente con prioridad manual.
        """
        pautas_por_id = {p.id: p for p in self._pautas}

        def peso_comercial_de(solicitud: PublicationRequest) -> Decimal:
            pauta = pautas_por_id.get(solicitud.pauta_id) if solicitud.pauta_id else None
            return pauta.peso_comercial if pauta is not None else Decimal("0")

        return sorted(
            self.solicitudes_pendientes(),
            key=lambda s: (not s.prioridad_manual, -peso_comercial_de(s), s.fecha_recepcion),
        )

    def solicitudes_publicadas(self) -> list[PublicationRequest]:
        """Return every `PublicationRequest` already published."""
        return [s for s in self._solicitudes if s.estado == PublicationRequestStatus.PUBLICADA]

    def solicitudes_antiguas(self, horas: int = 4) -> list[PublicationRequest]:
        """Return `RECIBIDA` requests that have waited at least `horas` hours.

        Only `RECIBIDA` requests qualify — one already `PUBLICADA` or
        `CANCELADA` is resolved, not "waiting".
        """
        limite = self._clock() - timedelta(hours=horas)
        return [s for s in self.solicitudes_pendientes() if s.fecha_recepcion <= limite]

    # ---------- helpers ----------

    def _pautas_de(self, client_id: str) -> list[Pauta]:
        return [p for p in self._pautas if p.client_id == client_id]

    def _ingresos_de(self, client_id: str) -> Decimal:
        return sum((p.valor_pagado for p in self._pautas_de(client_id)), start=Decimal("0"))

    def _tiene_cupo_bajo(self, pauta: Pauta) -> bool:
        restantes = self._pauta_service.publicaciones_restantes(pauta, self._solicitudes)
        proporcion = Decimal(restantes) / Decimal(pauta.publicaciones_contratadas)
        return proporcion < _CUPO_BAJO_UMBRAL

    def _contrato_de_referencia(self, pautas_cliente: Sequence[Pauta]) -> Pauta:
        """Return the one Pauta that represents a Client "right now" for display.

        Each Pauta is an independent contract — quota unused when one
        expires is gone, never inherited by the next one (functional
        review, 2026-08-05). So "the client's current contract" is the
        vigente Pauta that started most recently, if any; with no
        vigente Pauta at all, it falls back to the most recently
        *started* one overall, so a fully-expired client's card still
        has something concrete to show (clearly marked `vencido` via
        `estado_comercial`) instead of nothing. In the rare case of two
        simultaneously vigente Pautas, the newer one wins — it's the one
        an operator most likely means by "their current plan".
        """
        vigentes = [p for p in pautas_cliente if self._pauta_service.esta_vigente(p)]
        candidatas = vigentes or pautas_cliente
        return max(candidatas, key=lambda p: p.fecha_inicio)

    def _estado_comercial(self, pautas_cliente: Sequence[Pauta]) -> EstadoComercial:
        """Classify a Client's `EstadoComercial` from their own Pautas — see that enum.

        Deliberately recomputes "restantes" and "días para vencer" scoped
        to only the client's vigente Pautas — an expired Pauta's leftover
        quota or its already-past end date must never count toward
        "about to run out" or "about to expire", or a client with one
        old, fully-expired Pauta and one healthy new one could get
        flagged as urgent for no real reason. Sums across every
        currently-vigente Pauta rather than picking just one like
        `_contrato_de_referencia` does — unlike an expired contract, two
        Pautas that are *both* vigente right now are both genuinely
        actionable, so both counting toward "is this client healthy"
        is correct, not the same aggregation mistake.
        """
        vigentes = [p for p in pautas_cliente if self._pauta_service.esta_vigente(p)]
        if not vigentes:
            return EstadoComercial.VENCIDO
        restantes = sum(
            self._pauta_service.publicaciones_restantes(p, self._solicitudes) for p in vigentes
        )
        dias_para_vencer = min((p.fecha_fin - self._clock().date()).days for p in vigentes)
        if restantes <= 0 or dias_para_vencer <= _RENOVACION_DIAS:
            return EstadoComercial.RENOVACION
        if restantes <= _ATENCION_RESTANTES:
            return EstadoComercial.ATENCION
        return EstadoComercial.SALUDABLE
