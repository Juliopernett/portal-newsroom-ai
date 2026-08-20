"""Unit tests for MetaGraphSocialMediaReader — requests.get mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.meta_social.client import MetaGraphConfigurationError, MetaGraphSocialMediaReader
from config.settings import Settings
from core.entities.destino_publicacion import CanalPublicacion


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "meta_access_token": "a-fake-token",
        "meta_page_id": "page-123",
        "meta_instagram_business_account_id": "ig-456",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_raises_when_access_token_is_missing() -> None:
    with pytest.raises(MetaGraphConfigurationError):
        MetaGraphSocialMediaReader(_settings(meta_access_token=None))


def test_raises_when_page_id_is_missing() -> None:
    with pytest.raises(MetaGraphConfigurationError):
        MetaGraphSocialMediaReader(_settings(meta_page_id=None))


def test_raises_when_instagram_business_account_id_is_missing() -> None:
    with pytest.raises(MetaGraphConfigurationError):
        MetaGraphSocialMediaReader(_settings(meta_instagram_business_account_id=None))


def _mock_response(payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.json.return_value = payload
    return mock_response


def test_posts_facebook_exchanges_for_a_page_token_then_fetches_posts() -> None:
    """`/​{page}/posts` rejects the System User token directly (400
    OAuthException) — a Page-scoped token, obtained via `GET /{page}?
    fields=access_token`, is required first. See `_facebook_page_token`."""
    reader = MetaGraphSocialMediaReader(_settings())
    token_response = _mock_response({"access_token": "a-page-scoped-token"})
    posts_response = _mock_response(
        {
            "data": [
                {
                    "id": "123_456",
                    "message": "Nuevo sencillo disponible 🎶",
                    "permalink_url": "https://www.facebook.com/123_456",
                    "created_time": "2026-08-20T14:00:00+0000",
                    "full_picture": "https://scontent.xx/thumb.jpg",
                }
            ]
        }
    )

    with patch(
        "agents.meta_social.client.requests.get",
        side_effect=[token_response, posts_response],
    ) as mock_get:
        posts = reader.posts_recientes(CanalPublicacion.FACEBOOK, limite=5)

    assert len(posts) == 1
    post = posts[0]
    assert post.id == "123_456"
    assert post.canal == CanalPublicacion.FACEBOOK
    assert post.permalink == "https://www.facebook.com/123_456"
    assert post.texto == "Nuevo sencillo disponible 🎶"
    assert post.miniatura_url == "https://scontent.xx/thumb.jpg"

    token_args, token_kwargs = mock_get.call_args_list[0]
    assert token_args[0] == "https://graph.facebook.com/v21.0/page-123"
    assert token_kwargs["params"]["access_token"] == "a-fake-token"

    posts_args, posts_kwargs = mock_get.call_args_list[1]
    assert posts_args[0] == "https://graph.facebook.com/v21.0/page-123/posts"
    assert posts_kwargs["params"]["access_token"] == "a-page-scoped-token"
    assert posts_kwargs["params"]["limit"] == 5


def test_posts_facebook_caches_the_exchanged_page_token() -> None:
    reader = MetaGraphSocialMediaReader(_settings())
    token_response = _mock_response({"access_token": "a-page-scoped-token"})
    posts_response = _mock_response({"data": []})

    with patch(
        "agents.meta_social.client.requests.get",
        side_effect=[token_response, posts_response, posts_response],
    ) as mock_get:
        reader.posts_recientes(CanalPublicacion.FACEBOOK)
        reader.posts_recientes(CanalPublicacion.FACEBOOK)

    # Only one token exchange across both calls — three requests.get total,
    # not four.
    assert mock_get.call_count == 3


def test_posts_facebook_falls_back_when_message_is_missing() -> None:
    reader = MetaGraphSocialMediaReader(_settings())
    token_response = _mock_response({"access_token": "a-page-scoped-token"})
    posts_response = _mock_response(
        {"data": [{"id": "1", "created_time": "2026-08-20T14:00:00+0000"}]}
    )

    with patch(
        "agents.meta_social.client.requests.get",
        side_effect=[token_response, posts_response],
    ):
        posts = reader.posts_recientes(CanalPublicacion.FACEBOOK)

    assert posts[0].texto == "(sin texto)"
    assert posts[0].permalink == "https://www.facebook.com/1"


def test_posts_instagram_maps_the_graph_api_response() -> None:
    reader = MetaGraphSocialMediaReader(_settings())
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "id": "789",
                "caption": "Ensayo de esta tarde 🪗",
                "permalink": "https://www.instagram.com/p/789/",
                "timestamp": "2026-08-20T10:00:00+0000",
                "thumbnail_url": "https://scontent.xx/ig-thumb.jpg",
            }
        ]
    }

    with patch("agents.meta_social.client.requests.get", return_value=mock_response) as mock_get:
        posts = reader.posts_recientes(CanalPublicacion.INSTAGRAM)

    assert posts[0].canal == CanalPublicacion.INSTAGRAM
    assert posts[0].permalink == "https://www.instagram.com/p/789/"
    assert posts[0].miniatura_url == "https://scontent.xx/ig-thumb.jpg"
    args, _kwargs = mock_get.call_args
    assert args[0] == "https://graph.facebook.com/v21.0/ig-456/media"


def test_posts_recientes_rejects_wordpress() -> None:
    reader = MetaGraphSocialMediaReader(_settings())

    with pytest.raises(ValueError, match="no hay posts recientes"):
        reader.posts_recientes(CanalPublicacion.WORDPRESS)


def test_posts_recientes_raises_on_a_non_2xx_response() -> None:
    import requests

    reader = MetaGraphSocialMediaReader(_settings())
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")

    with (
        patch("agents.meta_social.client.requests.get", return_value=mock_response),
        pytest.raises(requests.HTTPError),
    ):
        reader.posts_recientes(CanalPublicacion.FACEBOOK)
