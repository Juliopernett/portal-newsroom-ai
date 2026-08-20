"""In-process rate limiter for login attempts (security audit 2026-08-20, M1).

`core.entities.user.User` deliberately has no lockout counters (ADR-005,
MVP scope) — this is a different, coarser thing: an ops-level brake on
brute force / credential stuffing against `POST /auth/login`, sitting
entirely outside the domain model.

Keyed by email, not by client IP: Railway terminates TLS in front of
uvicorn without `--proxy-headers` (see `docker/Dockerfile`), so
`request.client.host` is Railway's internal proxy address, not the real
caller's — an IP-keyed limiter would silently rate-limit nothing.

In-memory, not persisted: this app runs as a single Railway instance (no
horizontal scaling configured), so the state doesn't need to survive a
restart to do its job. Losing it on deploy is an acceptable tradeoff for
blocking brute force, not a security boundary that needs to survive one.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

MAX_INTENTOS = 5
VENTANA = timedelta(minutes=15)


class LoginRateLimiter:
    """Blocks a key (an email) after `max_intentos` failures within `ventana`."""

    def __init__(self, *, max_intentos: int = MAX_INTENTOS, ventana: timedelta = VENTANA) -> None:
        self._max_intentos = max_intentos
        self._ventana = ventana
        self._intentos: dict[str, list[datetime]] = defaultdict(list)

    def _vigentes(self, clave: str, ahora: datetime) -> list[datetime]:
        return [t for t in self._intentos[clave] if ahora - t < self._ventana]

    def esta_bloqueado(self, clave: str, *, ahora: datetime | None = None) -> bool:
        """Return whether `clave` has hit the failure limit within the window."""
        ahora = ahora if ahora is not None else datetime.now(UTC)
        return len(self._vigentes(clave, ahora)) >= self._max_intentos

    def registrar_intento_fallido(self, clave: str, *, ahora: datetime | None = None) -> None:
        """Record one more failed attempt for `clave`, pruning expired ones."""
        ahora = ahora if ahora is not None else datetime.now(UTC)
        self._intentos[clave] = [*self._vigentes(clave, ahora), ahora]

    def limpiar(self, clave: str) -> None:
        """Forget `clave`'s failures — called on a successful login."""
        self._intentos.pop(clave, None)
