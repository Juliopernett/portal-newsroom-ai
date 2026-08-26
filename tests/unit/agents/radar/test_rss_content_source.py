"""Unit tests for RssContentSource — requests.get mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from agents.radar.rss_content_source import RssContentSource
from core.entities.source import Source
from core.ports.content_source import ContentSourceError
from core.services.deduplication import generate_candidate_hash

_FEED_VALIDO = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Feed de prueba</title>
<item>
  <title>Peter Manjarres anuncia nuevo disco</title>
  <link>https://example.com/peter-manjarres-nuevo-disco</link>
  <description>El artista vallenato presento su nuevo material discografico.</description>
  <pubDate>Tue, 25 Aug 2026 10:00:00 GMT</pubDate>
  <guid>guid-peter-1</guid>
</item>
<item>
  <title>Silvestre Dangond en concierto</title>
  <link>https://example.com/silvestre-concierto</link>
  <description>Gran concierto en Valledupar.</description>
  <pubDate>Mon, 24 Aug 2026 08:30:00 GMT</pubDate>
  <guid>guid-silvestre-1</guid>
</item>
</channel>
</rss>
"""

_FEED_VACIO = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Feed vacio</title></channel></rss>
"""

_FEED_CON_ENTRADA_INCOMPLETA = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Feed con entrada incompleta</title>
<item>
  <description>Sin titulo ni enlace, no se puede usar.</description>
</item>
<item>
  <title>Noticia valida</title>
  <link>https://example.com/noticia-valida</link>
  <description>Esta si tiene todo.</description>
</item>
</channel>
</rss>
"""

_FEED_MALFORMADO = b"esto no es XML valido {{{ << >>"

_FEED_CON_RESUMEN_HTML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Feed con resumen HTML (estilo Google Noticias)</title>
<item>
  <title>Noticia con resumen envuelto en HTML</title>
  <link>https://example.com/noticia-html</link>
  <description>&lt;a href="https://news.google.com/rss/articles/xyz"
    target="_blank"&gt;Noticia con resumen envuelto en HTML&lt;/a&gt;&amp;nbsp;&amp;nbsp;
    &lt;font color="#6f6f6f"&gt;ELHERALDO.CO&lt;/font&gt;</description>
</item>
</channel>
</rss>
"""


def _source(**overrides: object) -> Source:
    defaults: dict[str, object] = {
        "id": "fuente-1",
        "name": "Feed de prueba",
        "type": "rss",
        "url": "https://example.com/feed.xml",
    }
    defaults.update(overrides)
    return Source(**defaults)


def _mock_response(content: bytes, status_ok: bool = True) -> MagicMock:
    response = MagicMock()
    response.content = content
    if not status_ok:
        response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    return response


def test_fetch_candidates_reads_a_valid_feed_correctly() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        return_value=_mock_response(_FEED_VALIDO),
    ) as mock_get:
        candidatos = adapter.fetch_candidates()

    assert len(candidatos) == 2
    args, kwargs = mock_get.call_args
    assert args[0] == "https://example.com/feed.xml"
    assert kwargs["timeout"] == 15


def test_fetch_candidates_normalizes_fields_correctly() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        return_value=_mock_response(_FEED_VALIDO),
    ):
        candidatos = adapter.fetch_candidates()

    primero = candidatos[0]
    assert primero.title == "Peter Manjarres anuncia nuevo disco"
    assert primero.url == "https://example.com/peter-manjarres-nuevo-disco"
    assert "nuevo material discografico" in primero.summary
    assert primero.published_at is not None
    assert primero.published_at.year == 2026
    assert primero.published_at.month == 8
    assert primero.published_at.day == 25
    assert primero.metadata == {"guid": "guid-peter-1"}
    assert primero.source == "fuente-1"


def test_fetch_candidates_computes_hash_with_the_shared_dedup_function() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        return_value=_mock_response(_FEED_VALIDO),
    ):
        candidatos = adapter.fetch_candidates()

    esperado = generate_candidate_hash(
        source="fuente-1", url="https://example.com/peter-manjarres-nuevo-disco"
    )
    assert candidatos[0].hash == esperado


def test_fetch_candidates_returns_empty_list_for_an_empty_feed() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        return_value=_mock_response(_FEED_VACIO),
    ):
        candidatos = adapter.fetch_candidates()

    assert candidatos == []


def test_fetch_candidates_skips_an_entry_missing_title_or_link() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        return_value=_mock_response(_FEED_CON_ENTRADA_INCOMPLETA),
    ):
        candidatos = adapter.fetch_candidates()

    assert len(candidatos) == 1
    assert candidatos[0].title == "Noticia valida"


def test_fetch_candidates_strips_html_markup_from_the_summary() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        return_value=_mock_response(_FEED_CON_RESUMEN_HTML),
    ):
        candidatos = adapter.fetch_candidates()

    assert len(candidatos) == 1
    resumen = candidatos[0].summary
    assert "<a href" not in resumen
    assert "<font" not in resumen
    assert "&nbsp;" not in resumen
    assert "ELHERALDO.CO" in resumen


def test_fetch_candidates_raises_content_source_error_on_network_failure() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        side_effect=requests.ConnectionError("no se pudo conectar"),
    ), pytest.raises(ContentSourceError):
        adapter.fetch_candidates()


def test_fetch_candidates_raises_content_source_error_on_a_non_2xx_response() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        return_value=_mock_response(b"", status_ok=False),
    ), pytest.raises(ContentSourceError):
        adapter.fetch_candidates()


def test_fetch_candidates_raises_content_source_error_on_a_malformed_feed() -> None:
    source = _source()
    adapter = RssContentSource(source)

    with patch(
        "agents.radar.rss_content_source.requests.get",
        return_value=_mock_response(_FEED_MALFORMADO),
    ), pytest.raises(ContentSourceError):
        adapter.fetch_candidates()
