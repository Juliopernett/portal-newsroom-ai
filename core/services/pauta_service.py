"""Domain service: Pauta quota and validity, always computed, never stored.

`PautaService` answers the questions Portal Vallenato currently answers by
hand in a spreadsheet: how many publications a `Pauta` has left, whether it
is still valid, and whether it is exhausted. Every number comes from
`Pauta` and its linked `PublicationRequest` history — nothing is kept as a
mutable counter, so there is never a stored value that can drift from what
actually happened.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta

from core.entities.pauta import Pauta
from core.entities.publication_request import PublicationRequest, PublicationRequestStatus


class PautaService:
    """Computes quota and validity for a `Pauta` from source data."""

    def __init__(self, clock: Callable[[], date] = lambda: datetime.now(UTC).date()) -> None:
        """`clock` is injectable so tests can control what "today" means."""
        self._clock = clock

    def publicaciones_consumidas(
        self, pauta: Pauta, solicitudes: Sequence[PublicationRequest]
    ) -> int:
        """Return how many of `pauta`'s requests have actually been published."""
        return sum(
            1
            for solicitud in solicitudes
            if solicitud.pauta_id == pauta.id
            and solicitud.estado == PublicationRequestStatus.PUBLICADA
        )

    def publicaciones_restantes(
        self, pauta: Pauta, solicitudes: Sequence[PublicationRequest]
    ) -> int:
        """Return how many contracted publications `pauta` has left."""
        return pauta.publicaciones_contratadas - self.publicaciones_consumidas(pauta, solicitudes)

    def esta_vigente(self, pauta: Pauta) -> bool:
        """Return whether `pauta` is within its contracted date range today."""
        hoy = self._clock()
        return pauta.fecha_inicio <= hoy <= pauta.fecha_fin

    def esta_vencida(self, pauta: Pauta) -> bool:
        """Return whether `pauta`'s end date has already passed."""
        return self._clock() > pauta.fecha_fin

    def cuota_agotada(self, pauta: Pauta, solicitudes: Sequence[PublicationRequest]) -> bool:
        """Return whether `pauta` has no contracted publications left."""
        consumidas = self.publicaciones_consumidas(pauta, solicitudes)
        return consumidas >= pauta.publicaciones_contratadas

    def pautas_por_vencer(self, pautas: Sequence[Pauta], dentro_de_dias: int) -> list[Pauta]:
        """Return `pautas` whose end date falls within the next `dentro_de_dias` days."""
        hoy = self._clock()
        limite = hoy + timedelta(days=dentro_de_dias)
        return [pauta for pauta in pautas if hoy <= pauta.fecha_fin <= limite]
