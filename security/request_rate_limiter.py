"""In-process sliding-window rate limiter keyed by an arbitrary string (an IP).

Complements `security.login_rate_limiter.LoginRateLimiter` (keyed by email):
that one stops brute force against one account, this one stops one caller
from hammering the app — failed logins across many emails, or the public
token-gated PDF routes (each hit renders a PDF, i.e. free CPU for an
attacker). Same tradeoffs: single instance, in-memory, lost on restart.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

_MAX_CLAVES = 10_000  # hard cap so random keys can't grow the dict forever


class RequestRateLimiter:
    """Allows at most `max_eventos` events per `ventana` for each key."""

    def __init__(self, *, max_eventos: int, ventana: timedelta) -> None:
        self._max = max_eventos
        self._ventana = ventana
        self._eventos: dict[str, list[datetime]] = {}

    def _purgar(self, ahora: datetime) -> None:
        if len(self._eventos) < _MAX_CLAVES:
            return
        for clave in list(self._eventos):
            vigentes = [t for t in self._eventos[clave] if ahora - t < self._ventana]
            if vigentes:
                self._eventos[clave] = vigentes
            else:
                del self._eventos[clave]
        if len(self._eventos) >= _MAX_CLAVES:  # still full of live keys: start over
            self._eventos.clear()

    def _vigentes(self, clave: str, ahora: datetime) -> list[datetime]:
        return [t for t in self._eventos.get(clave, []) if ahora - t < self._ventana]

    def esta_bloqueado(self, clave: str, *, ahora: datetime | None = None) -> bool:
        """Whether `clave` already used up its quota (does not record an event)."""
        ahora = ahora or datetime.now(UTC)
        return len(self._vigentes(clave, ahora)) >= self._max

    def registrar(self, clave: str, *, ahora: datetime | None = None) -> None:
        """Record one event for `clave`."""
        ahora = ahora or datetime.now(UTC)
        self._purgar(ahora)
        self._eventos[clave] = [*self._vigentes(clave, ahora), ahora]

    def limpiar(self, clave: str) -> None:
        self._eventos.pop(clave, None)

    def permitir(self, clave: str, *, ahora: datetime | None = None) -> bool:
        """Record an event and return whether it is within quota."""
        ahora = ahora or datetime.now(UTC)
        if self.esta_bloqueado(clave, ahora=ahora):
            return False
        self.registrar(clave, ahora=ahora)
        return True
