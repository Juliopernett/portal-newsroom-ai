"""Real `SourceResolver` adapter that follows HTTP redirects.

Sprint Discovery 3 (2026-08-29). Google News' RSS `link` is a
`news.google.com/rss/articles/...` URL — this adapter follows whatever
redirect chain the server sends (`requests`, `allow_redirects=True`) to
find the real article URL. `stream=True` so the response body is never
downloaded just to read the final `.url` — the connection is closed
immediately after headers arrive (see `resolve`'s own `with` block).

Known limitation, expected and documented rather than worked around:
some aggregators serve a client-side (JavaScript) redirect instead of a
real HTTP 3xx — this adapter cannot follow those (see
`agents/radar/README.md`). A candidate whose resolved URL is still on
the same host as the input is treated as a failed resolution, since that
almost always means the redirect never actually left the aggregator.
"""

from __future__ import annotations

from urllib.parse import urlparse

import requests

from core.ports.source_resolver import ResolvedSource, SourceResolverError
from shared.logger import get_logger

logger = get_logger(__name__)

_REQUEST_TIMEOUT_SECONDS = 15


class HttpRedirectSourceResolver:
    """`SourceResolver` implemented by following real HTTP redirects."""

    def __init__(self, *, timeout: int = _REQUEST_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout

    def resolve(self, url: str) -> ResolvedSource:
        """Follow `url`'s redirect chain and return where it ultimately lands.

        Never raises for a network failure, timeout, redirect loop, or a
        site that refuses the request — all reported as
        `ResolvedSource(success=False, ...)`. Only raises
        `SourceResolverError` for a programmer error (empty `url`).
        """
        if not url:
            raise SourceResolverError("url must not be empty")

        try:
            with requests.get(
                url,
                allow_redirects=True,
                stream=True,
                timeout=self._timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; PortalNewsroomAI/1.0)"},
            ) as response:
                response.raise_for_status()
                resolved_url = response.url
        except requests.TooManyRedirects as exc:
            logger.warning("Redirect loop resolviendo '%s': %s", url, exc)
            return ResolvedSource(
                success=False, resolved_url=None, error=f"Ciclo de redirects: {exc}"
            )
        except requests.Timeout as exc:
            logger.warning("Timeout resolviendo '%s': %s", url, exc)
            return ResolvedSource(success=False, resolved_url=None, error=f"Timeout: {exc}")
        except requests.RequestException as exc:
            logger.warning("No se pudo resolver '%s': %s", url, exc)
            return ResolvedSource(success=False, resolved_url=None, error=str(exc))

        if _mismo_host(url, resolved_url):
            logger.info(
                "'%s' no redirigió a otro dominio (posible redirect por JavaScript)", url
            )
            return ResolvedSource(
                success=False,
                resolved_url=None,
                error="La URL no redirigió a un dominio distinto — probablemente requiere "
                "JavaScript para redirigir (no soportado por este resolver)",
            )

        logger.info("Resuelto '%s' -> '%s'", url, resolved_url)
        return ResolvedSource(success=True, resolved_url=resolved_url, error=None)


def _mismo_host(original: str, resuelta: str) -> bool:
    return urlparse(original).netloc == urlparse(resuelta).netloc
