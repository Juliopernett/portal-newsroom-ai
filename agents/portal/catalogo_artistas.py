"""Catalogue of the artist pages on portalvallenato.com.

The `/artistas/` page lists every artist as `<li data-n="normalized name"><a href=…>`.
That grid is the single source of truth for which artists have a page, so the
chart reads it instead of keeping a second list. Cached in memory; any failure
returns the last good copy (or an empty catalogue) so the chart never breaks
because the website is slow.
"""

from __future__ import annotations

import html
import re
import threading
import time
from collections.abc import Callable

import requests

URL_ARTISTAS = "https://portalvallenato.com/artistas/"
_TTL_SEGUNDOS = 6 * 3600
_TTL_ERROR_SEGUNDOS = 300
_TIMEOUT_SEGUNDOS = 8
_TARJETA = re.compile(
    r'<li\s+data-n="([^"]+)"[^>]*>\s*<a\s+href="(https://portalvallenato\.com/[^"]+)"'
)


def parsear_catalogo(contenido: str) -> dict[str, str]:
    return {html.unescape(n).strip(): u for n, u in _TARJETA.findall(contenido)}


class CatalogoArtistas:
    def __init__(
        self,
        descargar: Callable[[], str] | None = None,
        ahora: Callable[[], float] = time.monotonic,
    ) -> None:
        self._descargar = descargar or self._descargar_web
        self._ahora = ahora
        self._lock = threading.Lock()
        self._datos: dict[str, str] = {}
        self._vence = 0.0

    @staticmethod
    def _descargar_web() -> str:
        r = requests.get(URL_ARTISTAS, timeout=_TIMEOUT_SEGUNDOS)
        r.raise_for_status()
        return r.text

    def obtener(self) -> dict[str, str]:
        with self._lock:
            if self._ahora() < self._vence:
                return self._datos
            try:
                nuevos = parsear_catalogo(self._descargar())
            except (requests.RequestException, ValueError):
                self._vence = self._ahora() + _TTL_ERROR_SEGUNDOS
                return self._datos
            if nuevos:
                self._datos = nuevos
                self._vence = self._ahora() + _TTL_SEGUNDOS
            else:
                self._vence = self._ahora() + _TTL_ERROR_SEGUNDOS
            return self._datos


_catalogo = CatalogoArtistas()


def get_catalogo_artistas() -> CatalogoArtistas:
    """FastAPI dependency; tests override it."""
    return _catalogo
