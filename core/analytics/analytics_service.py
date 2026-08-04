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
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from core.analytics.view_models import ClienteIngreso, ClientePesoComercial
from core.entities.client import Client
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus
from core.services.pauta_service import PautaService

_CUPO_BAJO_UMBRAL = Decimal("0.2")


class AnalyticsService:
    """Computes business metrics from a fixed snapshot of domain data."""

    def __init__(
        self,
        clients: Sequence[Client],
        pautas: Sequence[Pauta],
        solicitudes: Sequence[PublicationRequest],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
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

    def ingresos_activos(self) -> Decimal:
        """Return total `valor_pagado` across only currently-vigente `Pauta`s."""
        return sum((p.valor_pagado for p in self.pautas_activas()), start=Decimal("0"))

    def ingresos_historicos(self) -> Decimal:
        """Return total `valor_pagado` across every `Pauta`, past or present."""
        return sum((p.valor_pagado for p in self._pautas), start=Decimal("0"))

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
        """Return `Client`s with at least one `Pauta` whose quota is exhausted."""
        client_ids = {pauta.client_id for pauta in self.pautas_agotadas()}
        return [cliente for cliente in self._clients if cliente.id in client_ids]

    def clientes_con_cupo_bajo(self) -> list[Client]:
        """Return `Client`s with a `Pauta` at under 20% of its quota remaining.

        A business threshold, distinct from the presentation-only
        `LOW_QUOTA_THRESHOLD` (an absolute count of 2) in `app.js`, used
        only to decide what gets a warning badge on screen. The two are not
        required to agree — this one is a percentage of what was contracted,
        that one is a fixed headcount, and they serve different readers.
        """
        client_ids = {pauta.client_id for pauta in self._pautas if self._tiene_cupo_bajo(pauta)}
        return [cliente for cliente in self._clients if cliente.id in client_ids]

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
