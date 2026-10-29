"""Real `SourceResolver` adapter that decodes Google News article links.

Sprint Discovery 4 (2026-10-29). Google News' RSS `link` is a
`news.google.com/rss/articles/<id>` URL whose redirect is client-side
(JavaScript), so `HttpRedirectSourceResolver` fails on it 100% of the
time. This adapter does what the Google News web app itself does: reads
the per-article signature and timestamp off the article page, then asks
Google's internal `batchexecute` endpoint (`Fbv4je` RPC) for the real
URL. Verified against the live feed (20/20 resolved) when written.

Fragile by nature: this is an undocumented internal endpoint, so it can
break whenever Google changes it. Every failure is reported as
`ResolvedSource(success=False, ...)`, never raised, so the pipeline keeps
working (the candidate just stays "pendiente de resolver"). A non-Google
URL is handed to `fallback` untouched.
"""

from __future__ import annotations

import json
import re
from urllib.parse import quote, urlparse

import requests
from bs4 import BeautifulSoup

from core.ports.source_resolver import ResolvedSource, SourceResolver, SourceResolverError
from shared.logger import get_logger

logger = get_logger(__name__)

_REQUEST_TIMEOUT_SECONDS = 15
_GOOGLE_NEWS_HOST = "news.google.com"
_ARTICLE_PAGE_URL = "https://news.google.com/rss/articles/{article_id}"
_BATCHEXECUTE_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# The RPC response embeds the answer as an escaped JSON string: `garturlres\",\"<url>\"`.
_RESPONSE_URL_PATTERN = re.compile(r'garturlres\\",\\"(.*?)\\"')


class GoogleNewsSourceResolver:
    """`SourceResolver` that decodes `news.google.com/rss/articles/...` links."""

    def __init__(
        self, *, fallback: SourceResolver | None = None, timeout: int = _REQUEST_TIMEOUT_SECONDS
    ) -> None:
        self._fallback = fallback
        self._timeout = timeout

    def resolve(self, url: str) -> ResolvedSource:
        """Return the real article URL behind a Google News link.

        Never raises for a failure of the remote side — only
        `SourceResolverError` for an empty `url`.
        """
        if not url:
            raise SourceResolverError("url must not be empty")

        if urlparse(url).netloc != _GOOGLE_NEWS_HOST:
            if self._fallback is not None:
                return self._fallback.resolve(url)
            return ResolvedSource(
                success=False, resolved_url=None, error="No es un enlace de Google Noticias"
            )

        article_id = urlparse(url).path.rstrip("/").split("/")[-1]
        try:
            resolved_url = self._decode(article_id)
        except requests.Timeout as exc:
            logger.warning("Timeout decodificando '%s': %s", url, exc)
            return ResolvedSource(success=False, resolved_url=None, error=f"Timeout: {exc}")
        except requests.RequestException as exc:
            logger.warning("No se pudo decodificar '%s': %s", url, exc)
            return ResolvedSource(success=False, resolved_url=None, error=str(exc))
        except _DecodeError as exc:
            logger.warning("Google Noticias cambió su formato? '%s': %s", url, exc)
            return ResolvedSource(success=False, resolved_url=None, error=str(exc))

        logger.info("Resuelto '%s' -> '%s'", url, resolved_url)
        return ResolvedSource(success=True, resolved_url=resolved_url, error=None)

    def _decode(self, article_id: str) -> str:
        headers = {"User-Agent": _USER_AGENT}
        page = requests.get(
            _ARTICLE_PAGE_URL.format(article_id=article_id), headers=headers, timeout=self._timeout
        )
        page.raise_for_status()
        anchor = BeautifulSoup(page.text, "html.parser").select_one("c-wiz > div[jscontroller]")
        signature = anchor.get("data-n-a-sg") if anchor else None
        timestamp = anchor.get("data-n-a-ts") if anchor else None
        if not signature or not timestamp:
            raise _DecodeError("La página de Google Noticias no trae firma/timestamp del artículo")

        inner = [
            "garturlreq",
            [
                [
                    "X",
                    "X",
                    ["X", "X"],
                    None,
                    None,
                    1,
                    1,
                    "US:en",
                    None,
                    1,
                    None,
                    None,
                    None,
                    None,
                    None,
                    0,
                    1,
                ],
                "X",
                "X",
                1,
                [1, 1, 1],
                1,
                1,
                None,
                0,
                0,
                None,
                0,
            ],
            article_id,
            int(timestamp),
            signature,
        ]
        payload = [[["Fbv4je", json.dumps(inner), None, "generic"]]]
        response = requests.post(
            _BATCHEXECUTE_URL,
            headers={**headers, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
            data="f.req=" + quote(json.dumps(payload)),
            timeout=self._timeout,
        )
        response.raise_for_status()
        match = _RESPONSE_URL_PATTERN.search(response.text)
        if not match:
            raise _DecodeError("Google Noticias no devolvió la URL original del artículo")
        return match.group(1).encode().decode("unicode_escape")


class _DecodeError(Exception):
    """Internal: the remote answered, but not in the shape this adapter expects."""
