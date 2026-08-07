"""Unit tests for WordPressCMSPublisher — requests.post mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.wordpress.client import WordPressCMSPublisher, WordPressConfigurationError
from config.settings import Settings
from core.ports.cms_publisher import CMSDraftResult


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
