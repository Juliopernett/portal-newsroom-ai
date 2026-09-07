"""Unit tests for HtmlContentExtractor — requests.get mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from agents.extractor.html_content_extractor import HtmlContentExtractor
from core.ports.content_extractor import ContentExtractorError

_URL = "https://elpilon.com.co/noticia-real"

_PAGINA_COMPLETA = f"""
<html>
<head>
  <title>Titulo del tag title</title>
  <meta property="og:title" content="Un festival vallenato bate record de asistencia" />
  <meta property="og:site_name" content="El Pilon" />
  <meta property="og:image" content="https://elpilon.com.co/img/festival.jpg" />
  <meta property="article:published_time" content="2026-08-20T10:00:00Z" />
  <meta name="author" content="Redaccion El Pilon" />
</head>
<body>
  <article>
    <p>{"Miles de personas asistieron a la clausura del festival en Valledupar. " * 4}</p>
    <p>{"Los organizadores celebraron el exito de esta edicion del evento. " * 4}</p>
  </article>
</body>
</html>
"""

_PAGINA_SIN_ARTICLE = f"""
<html>
<head><title>Noticia sin article</title></head>
<body>
  <div class="noise"><p>Menu Inicio Contacto</p></div>
  <div class="content">
    <p>{"Este es el cuerpo real de la noticia, con suficiente texto para pasar el minimo. " * 6}</p>
  </div>
</body>
</html>
"""

_PAGINA_VACIA = """
<html><head><title>Requiere JavaScript</title></head>
<body><div id="root"></div></body></html>
"""


def _mock_response(html: str, status_ok: bool = True) -> MagicMock:
    response = MagicMock()
    response.text = html
    if not status_ok:
        response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    return response


def test_extract_reads_meta_tags_when_available() -> None:
    extractor = HtmlContentExtractor()

    with patch(
        "agents.extractor.html_content_extractor.requests.get",
        return_value=_mock_response(_PAGINA_COMPLETA),
    ) as mock_get:
        contenido = extractor.extract(_URL)

    assert contenido.title == "Un festival vallenato bate record de asistencia"
    assert contenido.site_name == "El Pilon"
    assert contenido.author == "Redaccion El Pilon"
    assert contenido.image_urls == ("https://elpilon.com.co/img/festival.jpg",)
    assert contenido.published_at is not None
    assert contenido.published_at.year == 2026
    assert "clausura del festival" in contenido.body
    assert contenido.source_url == _URL
    args, kwargs = mock_get.call_args
    assert args[0] == _URL
    assert kwargs["timeout"] == 20


def test_extract_falls_back_to_densest_block_without_an_article_tag() -> None:
    extractor = HtmlContentExtractor()

    with patch(
        "agents.extractor.html_content_extractor.requests.get",
        return_value=_mock_response(_PAGINA_SIN_ARTICLE),
    ):
        contenido = extractor.extract(_URL)

    assert "cuerpo real de la noticia" in contenido.body
    assert "Menu Inicio Contacto" not in contenido.body
    assert contenido.title == "Noticia sin article"
    assert contenido.author is None
    assert contenido.site_name is None


def test_extract_raises_when_the_page_has_no_recognizable_content() -> None:
    """A near-empty body is what a JS-rendered page looks like to a plain HTTP fetch."""
    extractor = HtmlContentExtractor()

    with patch(
        "agents.extractor.html_content_extractor.requests.get",
        return_value=_mock_response(_PAGINA_VACIA),
    ), pytest.raises(ContentExtractorError):
        extractor.extract(_URL)


def test_extract_raises_content_extractor_error_on_network_failure() -> None:
    extractor = HtmlContentExtractor()

    with patch(
        "agents.extractor.html_content_extractor.requests.get",
        side_effect=requests.ConnectionError("no se pudo conectar"),
    ), pytest.raises(ContentExtractorError):
        extractor.extract(_URL)


def test_extract_raises_content_extractor_error_on_a_non_2xx_response() -> None:
    extractor = HtmlContentExtractor()

    with patch(
        "agents.extractor.html_content_extractor.requests.get",
        return_value=_mock_response("", status_ok=False),
    ), pytest.raises(ContentExtractorError):
        extractor.extract(_URL)


def test_extract_raises_content_extractor_error_on_timeout() -> None:
    extractor = HtmlContentExtractor()

    with patch(
        "agents.extractor.html_content_extractor.requests.get",
        side_effect=requests.Timeout("tardó demasiado"),
    ), pytest.raises(ContentExtractorError):
        extractor.extract(_URL)
