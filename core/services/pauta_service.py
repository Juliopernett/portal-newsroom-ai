"""Domain service: Pauta quota and validity, always computed, never stored.

`PautaService` answers the questions Portal Vallenato currently answers by
hand in a spreadsheet: how many publications a `Pauta` has left, whether it
is still valid, and whether it is exhausted. Every number comes from
`Pauta` and its linked `PublicationRequest`/`DestinoPublicacion` history —
nothing is kept as a mutable counter, so there is never a stored value
that can drift from what actually happened.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date, timedelta

from core.clock import now_local
from core.entities.destino_publicacion import DestinoPublicacion
from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest
from core.services.destino_publicacion_service import esta_completa


class PautaService:
    """Computes quota and validity for a `Pauta` from source data."""

    def __init__(self, clock: Callable[[], date] = lambda: now_local().date()) -> None:
        """`clock` is injectable so tests can control what "today" means."""
        self._clock = clock

    def publicaciones_consumidas(
        self,
        pauta: Pauta,
        solicitudes: Sequence[PublicationRequest],
        destinos: Sequence[DestinoPublicacion],
    ) -> int:
        """Return how many of `pauta`'s requests are complete.

        Sprint 4A, Increment 4 (see
        docs/adr/ADR-006-multichannel-publication.md, Decision 3):
        "complete" is `esta_completa` over each solicitud's own
        `DestinoPublicacion`s — not `estado == PUBLICADA` (that value was
        retired; `estado` now describes only intake triage, see
        `core.entities.publication_request`). A solicitud with several
        destinos still counts once, never once per destino.
        """
        destinos_por_solicitud: dict[str, list[DestinoPublicacion]] = {}
        for destino in destinos:
            destinos_por_solicitud.setdefault(destino.publication_request_id, []).append(destino)
        return sum(
            1
            for solicitud in solicitudes
            if solicitud.pauta_id == pauta.id
            and esta_completa(destinos_por_solicitud.get(solicitud.id, []))
        )

    def publicaciones_restantes(
        self,
        pauta: Pauta,
        solicitudes: Sequence[PublicationRequest],
        destinos: Sequence[DestinoPublicacion],
    ) -> int:
        """Return how many contracted publications `pauta` has left."""
        return pauta.publicaciones_contratadas - self.publicaciones_consumidas(
            pauta, solicitudes, destinos
        )

    def esta_vigente(self, pauta: Pauta) -> bool:
        """Return whether `pauta` is within its contracted date range today."""
        hoy = self._clock()
        return pauta.fecha_inicio <= hoy <= pauta.fecha_fin

    def esta_vencida(self, pauta: Pauta) -> bool:
        """Return whether `pauta`'s end date has already passed."""
        return self._clock() > pauta.fecha_fin

    def cuota_agotada(
        self,
        pauta: Pauta,
        solicitudes: Sequence[PublicationRequest],
        destinos: Sequence[DestinoPublicacion],
    ) -> bool:
        """Return whether `pauta` has no contracted publications left."""
        consumidas = self.publicaciones_consumidas(pauta, solicitudes, destinos)
        return consumidas >= pauta.publicaciones_contratadas

    def pautas_por_vencer(self, pautas: Sequence[Pauta], dentro_de_dias: int) -> list[Pauta]:
        """Return `pautas` whose end date falls within the next `dentro_de_dias` days."""
        hoy = self._clock()
        limite = hoy + timedelta(days=dentro_de_dias)
        return [pauta for pauta in pautas if hoy <= pauta.fecha_fin <= limite]
