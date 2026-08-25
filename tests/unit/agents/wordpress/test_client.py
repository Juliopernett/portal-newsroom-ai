"""Unit tests for WordPressCMSPublisher — requests.post mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from datetime import UTC, datetime

from agents.wordpress.client import WordPressCMSPublisher, WordPressConfigurationError
from config.settings import Settings
from core.ports.cms_publisher import CategoriaCMS, CMSDraftResult, ConsultaPostCMS, EstadoPostCMS


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "wordpress_site_url": "https://www.portalvallenato.com",
        "wordpress_username": "editor",
        "wordpress_app_password": "abcd efgh ijkl mnop",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_raises_when_site_url_is_missing() -> None:
    with pytest.raises(WordPressConfigurationError):
        WordPressCMSPublisher(_settings(wordpress_site_url=None))


def test_raises_when_username_is_missing() -> None:
    with pytest.raises(WordPressConfigurationError):
        WordPressCMSPublisher(_settings(wordpress_username=None))


def test_raises_when_app_password_is_missing() -> None:
    with pytest.raises(WordPressConfigurationError):
        WordPressCMSPublisher(_settings(wordpress_app_password=None))


def test_create_draft_posts_status_draft_never_publish() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 42, "link": "https://www.portalvallenato.com/?p=42"}

    with patch("agents.wordpress.client.requests.post", return_value=mock_response) as mock_post:
        resultado = publisher.create_draft({"title": "Titulo", "content": "Cuerpo"})

    assert resultado == CMSDraftResult(post_id="42", url="https://www.portalvallenato.com/?p=42")
    _args, kwargs = mock_post.call_args
    assert kwargs["json"]["status"] == "draft"
    assert kwargs["json"]["title"] == "Titulo"
    assert kwargs["json"]["content"] == "Cuerpo"
    mock_response.raise_for_status.assert_called_once()


def test_create_draft_authenticates_with_username_and_app_password() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "link": "https://example.com/?p=1"}

    with patch("agents.wordpress.client.requests.post", return_value=mock_response) as mock_post:
        publisher.create_draft({"title": "T", "content": "C"})

    _args, kwargs = mock_post.call_args
    assert kwargs["auth"] == ("editor", "abcd efgh ijkl mnop")


def test_create_draft_targets_the_configured_site_posts_endpoint() -> None:
    publisher = WordPressCMSPublisher(_settings(wordpress_site_url="https://example.com/"))
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "link": "https://example.com/?p=1"}

    with patch("agents.wordpress.client.requests.post", return_value=mock_response) as mock_post:
        publisher.create_draft({"title": "T", "content": "C"})

    args, _kwargs = mock_post.call_args
    assert args[0] == "https://example.com/wp-json/wp/v2/posts"


def test_create_draft_raises_on_a_non_2xx_response() -> None:
    import requests

    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")

    with (
        patch("agents.wordpress.client.requests.post", return_value=mock_response),
        pytest.raises(requests.HTTPError),
    ):
        publisher.create_draft({"title": "T", "content": "C"})


def test_create_draft_forwards_optional_fields_as_wordpress_ids() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "link": "https://example.com/?p=1"}

    with patch("agents.wordpress.client.requests.post", return_value=mock_response) as mock_post:
        publisher.create_draft(
            {
                "title": "T",
                "content": "C",
                "excerpt": "Entradilla",
                "slug": "titulo",
                "categories": ["7"],
                "tags": ["3", "9"],
                "featured_media": "12",
                "meta": {
                    "_yoast_wpseo_title": "Meta título",
                    "_yoast_wpseo_metadesc": "Meta descripción",
                    "_yoast_wpseo_focuskw": "frase clave",
                },
            }
        )

    _args, kwargs = mock_post.call_args
    assert kwargs["json"]["excerpt"] == "Entradilla"
    assert kwargs["json"]["slug"] == "titulo"
    assert kwargs["json"]["categories"] == [7]
    assert kwargs["json"]["tags"] == [3, 9]
    assert kwargs["json"]["featured_media"] == 12
    assert kwargs["json"]["meta"] == {
        "_yoast_wpseo_title": "Meta título",
        "_yoast_wpseo_metadesc": "Meta descripción",
        "_yoast_wpseo_focuskw": "frase clave",
    }


def test_create_draft_omits_optional_fields_when_absent() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "link": "https://example.com/?p=1"}

    with patch("agents.wordpress.client.requests.post", return_value=mock_response) as mock_post:
        publisher.create_draft({"title": "T", "content": "C"})

    _args, kwargs = mock_post.call_args
    assert set(kwargs["json"]) == {"title", "content", "status"}


def test_listar_categorias_returns_id_and_name_pairs() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": 3, "name": "Noticias"},
        {"id": 7, "name": "Crónicas"},
    ]

    with patch("agents.wordpress.client.requests.get", return_value=mock_response) as mock_get:
        resultado = publisher.listar_categorias()

    assert resultado == [CategoriaCMS(id="3", nombre="Noticias"), CategoriaCMS(id="7", nombre="Crónicas")]
    args, _kwargs = mock_get.call_args
    assert args[0] == "https://www.portalvallenato.com/wp-json/wp/v2/categories"
    mock_response.raise_for_status.assert_called_once()


def test_resolver_o_crear_etiqueta_reuses_an_existing_tag() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_search = MagicMock()
    mock_search.json.return_value = [{"id": 5, "name": "vallenato"}]

    with patch("agents.wordpress.client.requests.get", return_value=mock_search) as mock_get:
        with patch("agents.wordpress.client.requests.post") as mock_post:
            resultado = publisher.resolver_o_crear_etiqueta("vallenato")

    assert resultado == "5"
    mock_post.assert_not_called()
    _args, kwargs = mock_get.call_args
    assert kwargs["params"] == {"search": "vallenato"}


def test_resolver_o_crear_etiqueta_creates_a_new_tag_when_not_found() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_search = MagicMock()
    mock_search.json.return_value = []
    mock_create = MagicMock()
    mock_create.json.return_value = {"id": 11, "name": "nueva-etiqueta"}

    with patch("agents.wordpress.client.requests.get", return_value=mock_search):
        with patch(
            "agents.wordpress.client.requests.post", return_value=mock_create
        ) as mock_post:
            resultado = publisher.resolver_o_crear_etiqueta("nueva-etiqueta")

    assert resultado == "11"
    _args, kwargs = mock_post.call_args
    assert kwargs["json"] == {"name": "nueva-etiqueta"}


def test_resolver_o_crear_etiqueta_reuses_the_term_id_wordpress_reports_on_a_conflict() -> None:
    """Reproduced live against the real site (2026-08-25): creating a tag whose
    name/slug already exists returns 400 term_exists with the existing term_id
    in the error body, even though the prior search call missed it — this must
    resolve to that id instead of raising and aborting the whole draft."""
    publisher = WordPressCMSPublisher(_settings())
    mock_search = MagicMock()
    mock_search.json.return_value = []
    mock_create = MagicMock()
    mock_create.status_code = 400
    mock_create.json.return_value = {
        "code": "term_exists",
        "message": "Ya existe en esta taxonomía un término con el nombre y el slug facilitados.",
        "data": {"status": 400, "term_id": 572},
    }

    with patch("agents.wordpress.client.requests.get", return_value=mock_search):
        with patch(
            "agents.wordpress.client.requests.post", return_value=mock_create
        ) as mock_post:
            resultado = publisher.resolver_o_crear_etiqueta("Karen Lizarazo")

    assert resultado == "572"
    mock_create.raise_for_status.assert_not_called()
    _args, kwargs = mock_post.call_args
    assert kwargs["json"] == {"name": "Karen Lizarazo"}


def test_resolver_o_crear_etiqueta_raises_on_a_400_that_is_not_term_exists() -> None:
    import requests

    publisher = WordPressCMSPublisher(_settings())
    mock_search = MagicMock()
    mock_search.json.return_value = []
    mock_create = MagicMock()
    mock_create.status_code = 400
    mock_create.json.return_value = {"code": "empty_term_name", "message": "..."}
    mock_create.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")

    with patch("agents.wordpress.client.requests.get", return_value=mock_search):
        with patch("agents.wordpress.client.requests.post", return_value=mock_create):
            with pytest.raises(requests.HTTPError):
                publisher.resolver_o_crear_etiqueta("")


def test_subir_media_sends_content_disposition_and_returns_id() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 21}

    with patch("agents.wordpress.client.requests.post", return_value=mock_response) as mock_post:
        resultado = publisher.subir_media(b"contenido", "foto.jpg", "image/jpeg")

    assert resultado == "21"
    _args, kwargs = mock_post.call_args
    assert kwargs["data"] == b"contenido"
    assert kwargs["headers"]["Content-Disposition"] == 'attachment; filename="foto.jpg"'
    assert kwargs["headers"]["Content-Type"] == "image/jpeg"


def test_consultar_estado_post_maps_publish_to_publicado_with_url_and_fecha() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "status": "publish",
        "link": "https://www.portalvallenato.com/nota-real/",
        "date_gmt": "2026-08-24T15:30:00",
    }

    with patch("agents.wordpress.client.requests.get", return_value=mock_response) as mock_get:
        resultado = publisher.consultar_estado_post("42")

    assert resultado == ConsultaPostCMS(
        estado=EstadoPostCMS.PUBLICADO,
        url="https://www.portalvallenato.com/nota-real/",
        fecha_publicacion=datetime(2026, 8, 24, 15, 30, tzinfo=UTC),
    )
    args, kwargs = mock_get.call_args
    assert args[0] == "https://www.portalvallenato.com/wp-json/wp/v2/posts/42"
    assert kwargs["params"] == {"context": "edit"}


def test_consultar_estado_post_maps_trash_to_eliminado() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"status": "trash"}

    with patch("agents.wordpress.client.requests.get", return_value=mock_response):
        resultado = publisher.consultar_estado_post("42")

    assert resultado == ConsultaPostCMS(estado=EstadoPostCMS.ELIMINADO, url=None, fecha_publicacion=None)


def test_consultar_estado_post_maps_draft_to_borrador() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {"status": "draft"}

    with patch("agents.wordpress.client.requests.get", return_value=mock_response):
        resultado = publisher.consultar_estado_post("42")

    assert resultado == ConsultaPostCMS(estado=EstadoPostCMS.BORRADOR, url=None, fecha_publicacion=None)


def test_consultar_estado_post_maps_a_404_to_error() -> None:
    publisher = WordPressCMSPublisher(_settings())
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = 404

    with patch("agents.wordpress.client.requests.get", return_value=mock_response):
        resultado = publisher.consultar_estado_post("42")

    assert resultado == ConsultaPostCMS(estado=EstadoPostCMS.ERROR, url=None, fecha_publicacion=None)


def test_consultar_estado_post_maps_a_network_error_to_error_without_raising() -> None:
    import requests

    publisher = WordPressCMSPublisher(_settings())

    with patch(
        "agents.wordpress.client.requests.get", side_effect=requests.ConnectionError("timeout")
    ):
        resultado = publisher.consultar_estado_post("42")

    assert resultado == ConsultaPostCMS(estado=EstadoPostCMS.ERROR, url=None, fecha_publicacion=None)
