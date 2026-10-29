"""`FeedDetector` adapter: finds the RSS/Atom feed behind a website address.

Sprint Fuentes (2026-10-29). Order of attempts, stopping at the first
usable feed, with a hard cap of `_MAX_INTENTOS` requests so a hostile or
slow site can't keep a worker busy:

1. The address itself (the operator may have pasted the feed URL).
2. `<link rel="alternate" type="application/rss+xml|atom+xml">` in its HTML.
3. The usual paths: `/feed/`, `/feed`, `/rss.xml`, `/rss`, `/atom.xml`.

Every URL — including ones found inside the page — must be a public
address (see `agents.radar.url_segura`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from agents.radar.url_segura import UrlNoPermitidaError, validar_url_publica
from core.ports.feed_detector import EntradaFeed, FeedDetectado, FeedDetectorError

_TIMEOUT_SECONDS = 10
_MAX_INTENTOS = 6
_MAX_BYTES = 5 * 1024 * 1024
_ENTRADAS_VISTA_PREVIA = 5
_RUTAS_COMUNES = ("/feed/", "/feed", "/rss.xml", "/rss", "/atom.xml")
_USER_AGENT = "Mozilla/5.0 (compatible; PortalNewsroomAI/1.0; +https://portalvallenato.com)"
_TIPOS_FEED = ("application/rss+xml", "application/atom+xml", "application/xml", "text/xml")


class HttpFeedDetector:
    """`FeedDetector` implemented with plain HTTP requests."""

    def __init__(self, *, timeout: int = _TIMEOUT_SECONDS) -> None:
        self._timeout = timeout
        self._intentos = 0

    def detectar(self, url: str) -> FeedDetectado | None:
        self._intentos = 0
        inicial = _normalizar(url)
        try:
            validar_url_publica(inicial)
        except UrlNoPermitidaError as exc:
            raise FeedDetectorError(str(exc)) from exc

        respuesta = self._get(inicial)
        if respuesta is None:
            raise FeedDetectorError(f"No se pudo abrir {inicial}")
        feed = _como_feed(respuesta)
        if feed is not None:
            return feed

        for candidato in self._enlaces_en_html(respuesta, inicial) + [
            urljoin(inicial, ruta) for ruta in _RUTAS_COMUNES
        ]:
            if self._intentos >= _MAX_INTENTOS:
                break
            try:
                validar_url_publica(candidato)
            except UrlNoPermitidaError:
                continue
            extra = self._get(candidato)
            feed = _como_feed(extra) if extra is not None else None
            if feed is not None:
                return feed
        return None

    def _get(self, url: str) -> requests.Response | None:
        self._intentos += 1
        try:
            respuesta = requests.get(
                url, headers={"User-Agent": _USER_AGENT}, timeout=self._timeout
            )
            respuesta.raise_for_status()
        except requests.RequestException:
            return None
        if len(respuesta.content) > _MAX_BYTES:
            return None
        return respuesta

    @staticmethod
    def _enlaces_en_html(respuesta: requests.Response, base: str) -> list[str]:
        if "html" not in respuesta.headers.get("Content-Type", "").lower():
            return []
        sopa = BeautifulSoup(respuesta.text, "html.parser")
        enlaces: list[str] = []
        for etiqueta in sopa.find_all("link", rel="alternate"):
            tipo = str(etiqueta.get("type", "")).lower()
            href = etiqueta.get("href")
            if href and tipo in _TIPOS_FEED:
                enlaces.append(urljoin(base, str(href)))
        return enlaces


def _normalizar(url: str) -> str:
    url = url.strip()
    return url if "://" in url else f"https://{url}"


def _como_feed(respuesta: requests.Response) -> FeedDetectado | None:
    parseado = feedparser.parse(respuesta.content)
    if not parseado.entries:
        return None
    entradas = tuple(
        EntradaFeed(titulo=str(e.get("title", "")).strip(), publicada=_fecha(e))
        for e in parseado.entries[:_ENTRADAS_VISTA_PREVIA]
        if e.get("title")
    )
    if not entradas:
        return None
    titulo = str(parseado.feed.get("title") or urlparse(respuesta.url).hostname or "")
    return FeedDetectado(feed_url=respuesta.url, titulo=titulo.strip(), entradas=entradas)


def _fecha(entry: feedparser.FeedParserDict) -> datetime | None:
    parsed = entry.get("published_parsed")
    return datetime(*parsed[:6], tzinfo=UTC) if parsed else None
