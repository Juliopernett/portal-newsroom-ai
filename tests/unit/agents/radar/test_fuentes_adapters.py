"""Unit tests for the Sprint Fuentes adapters — URL guard, feed detector, conditional RSS fetch.

`socket.getaddrinfo` and `requests.get` are mocked: no DNS, no network.
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest
import requests

from agents.radar.feed_detector import HttpFeedDetector
from agents.radar.rss_content_source import RssContentSource
from agents.radar.url_segura import UrlNoPermitidaError, validar_url_publica
from core.entities.source import Source
from core.ports.content_source import ContentSourceError
from core.ports.feed_detector import FeedDetectorError

_RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Blog Vallenato</title>
<item><title>Nota uno</title><link>https://blog.example/uno</link>
<pubDate>Wed, 28 Oct 2026 10:00:00 GMT</pubDate></item>
<item><title>Nota dos</title><link>https://blog.example/dos</link></item>
</channel></rss>"""


def _dns(*ips: str):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0)) for ip in ips]


def _respuesta(
    contenido: bytes,
    *,
    url: str = "https://blog.example/feed/",
    content_type: str = "application/rss+xml",
    status: int = 200,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.content = contenido
    r.text = contenido.decode("utf-8", errors="ignore")
    r.url = url
    r.headers = {"Content-Type": content_type, **(headers or {})}
    r.raise_for_status.return_value = None
    return r


@pytest.fixture(autouse=True)
def _dns_publico():
    with patch("agents.radar.url_segura.socket.getaddrinfo", return_value=_dns("93.184.216.34")):
        yield


# --- url_segura ------------------------------------------------------------


def test_accepts_a_public_http_address() -> None:
    validar_url_publica("https://blog.example/feed")


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1"])
def test_rejects_internal_addresses(ip: str) -> None:
    with (
        patch("agents.radar.url_segura.socket.getaddrinfo", return_value=_dns(ip)),
        pytest.raises(UrlNoPermitidaError),
    ):
        validar_url_publica("https://evil.example/")


def test_rejects_non_http_schemes_and_missing_hosts() -> None:
    for url in ("ftp://blog.example/", "file:///etc/passwd", "https:///sin-host"):
        with pytest.raises(UrlNoPermitidaError):
            validar_url_publica(url)


def test_rejects_a_name_that_does_not_resolve() -> None:
    with (
        patch("agents.radar.url_segura.socket.getaddrinfo", side_effect=socket.gaierror),
        pytest.raises(UrlNoPermitidaError),
    ):
        validar_url_publica("https://no-existe.example/")


# --- feed detector ----------------------------------------------------------


def test_detector_accepts_a_feed_url_pasted_directly() -> None:
    with patch("agents.radar.feed_detector.requests.get", return_value=_respuesta(_RSS)):
        feed = HttpFeedDetector().detectar("https://blog.example/feed/")

    assert feed is not None
    assert feed.titulo == "Blog Vallenato"
    assert [e.titulo for e in feed.entradas] == ["Nota uno", "Nota dos"]
    assert feed.entradas[0].publicada is not None


def test_detector_follows_the_alternate_link_in_the_html() -> None:
    html = (
        b'<html><head><link rel="alternate" type="application/rss+xml" '
        b'href="/noticias.xml"></head></html>'
    )
    llamadas: list[str] = []

    def _get(url: str, **_: object) -> MagicMock:
        llamadas.append(url)
        if url.endswith("/noticias.xml"):
            return _respuesta(_RSS, url=url)
        return _respuesta(html, url=url, content_type="text/html")

    with patch("agents.radar.feed_detector.requests.get", side_effect=_get):
        feed = HttpFeedDetector().detectar("blog.example")

    assert feed is not None
    assert feed.feed_url == "https://blog.example/noticias.xml"
    assert llamadas == ["https://blog.example", "https://blog.example/noticias.xml"]


def test_detector_falls_back_to_the_usual_paths() -> None:
    def _get(url: str, **_: object) -> MagicMock:
        if url.endswith("/rss.xml"):
            return _respuesta(_RSS, url=url)
        return _respuesta(b"<html></html>", url=url, content_type="text/html")

    with patch("agents.radar.feed_detector.requests.get", side_effect=_get):
        feed = HttpFeedDetector().detectar("https://blog.example")

    assert feed is not None
    assert feed.feed_url.endswith("/rss.xml")


def test_detector_returns_none_for_a_site_without_feed_and_caps_requests() -> None:
    llamadas = []

    def _get(url: str, **_: object) -> MagicMock:
        llamadas.append(url)
        return _respuesta(b"<html></html>", url=url, content_type="text/html")

    with patch("agents.radar.feed_detector.requests.get", side_effect=_get):
        feed = HttpFeedDetector().detectar("https://blog.example")

    assert feed is None
    assert len(llamadas) <= 6


def test_detector_rejects_an_internal_address_without_requesting_it() -> None:
    with (
        patch("agents.radar.url_segura.socket.getaddrinfo", return_value=_dns("127.0.0.1")),
        patch("agents.radar.feed_detector.requests.get") as mock_get,
        pytest.raises(FeedDetectorError),
    ):
        HttpFeedDetector().detectar("http://localhost/feed")

    mock_get.assert_not_called()


def test_detector_reports_an_unreachable_site() -> None:
    with (
        patch("agents.radar.feed_detector.requests.get", side_effect=requests.ConnectionError),
        pytest.raises(FeedDetectorError),
    ):
        HttpFeedDetector().detectar("https://blog.example")


# --- conditional RSS fetch ---------------------------------------------------


def _fuente() -> Source:
    return Source(id="blog", name="Blog", type="rss", url="https://blog.example/feed/")


def test_rss_sends_the_validators_and_returns_the_new_ones() -> None:
    respuesta = _respuesta(_RSS, headers={"ETag": '"abc"', "Last-Modified": "Wed, 28 Oct 2026"})

    with patch("agents.radar.rss_content_source.requests.get", return_value=respuesta) as mock_get:
        resultado = RssContentSource(_fuente()).fetch_condicional('"viejo"', "Tue, 27 Oct 2026")

    headers = mock_get.call_args.kwargs["headers"]
    assert headers["If-None-Match"] == '"viejo"'
    assert headers["If-Modified-Since"] == "Tue, 27 Oct 2026"
    assert resultado.not_modified is False
    assert (resultado.etag, resultado.last_modified) == ('"abc"', "Wed, 28 Oct 2026")
    assert [c.title for c in resultado.candidates] == ["Nota uno", "Nota dos"]


def test_rss_answers_not_modified_without_parsing_anything() -> None:
    respuesta = _respuesta(b"", status=304)

    with patch("agents.radar.rss_content_source.requests.get", return_value=respuesta):
        resultado = RssContentSource(_fuente()).fetch_condicional('"abc"', None)

    assert resultado.not_modified is True
    assert resultado.candidates == []
    assert resultado.etag == '"abc"'


def test_rss_refuses_an_internal_address_when_validation_is_on() -> None:
    with (
        patch("agents.radar.url_segura.socket.getaddrinfo", return_value=_dns("10.0.0.7")),
        patch("agents.radar.rss_content_source.requests.get") as mock_get,
        pytest.raises(ContentSourceError),
    ):
        RssContentSource(_fuente(), validar_url=True).fetch_condicional(None, None)

    mock_get.assert_not_called()
