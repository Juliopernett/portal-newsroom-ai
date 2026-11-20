"""Download the few public images the weekly chart cards need.

Only the website's own uploads and YouTube thumbnails are fetched (an explicit
host allow-list, no redirects), with a short timeout and a size cap, so a bad
URL in the data can never turn the server into a proxy. Any failure just means
"no picture": the card falls back to initials / a plain block.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests

_HOSTS_EXACTOS = {"portalvallenato.com", "www.portalvallenato.com"}
_SUFIJOS = (".ytimg.com",)
_TIMEOUT_SEGUNDOS = 6
_MAX_BYTES = 6 * 1024 * 1024
_HILOS = 8


def _permitida(url: str) -> bool:
    partes = urlparse(url)
    host = (partes.hostname or "").lower()
    return partes.scheme == "https" and (host in _HOSTS_EXACTOS or host.endswith(_SUFIJOS))


def _bajar(url: str) -> bytes | None:
    if not _permitida(url):
        return None
    try:
        with requests.get(url, timeout=_TIMEOUT_SEGUNDOS, stream=True, allow_redirects=False) as r:
            if r.status_code != 200:
                return None
            datos = bytearray()
            for trozo in r.iter_content(64 * 1024):
                datos.extend(trozo)
                if len(datos) > _MAX_BYTES:
                    return None
            return bytes(datos)
    except requests.RequestException:
        return None


def descargar_imagenes(urls: list[str]) -> dict[str, bytes]:
    """URL -> image bytes for every URL that could be fetched (the rest are omitted)."""
    unicas = sorted({u for u in urls if u})
    if not unicas:
        return {}
    with ThreadPoolExecutor(max_workers=_HILOS) as pool:
        resultados = list(pool.map(_bajar, unicas))
    return {u: d for u, d in zip(unicas, resultados, strict=True) if d}
