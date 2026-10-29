"""Unit tests for GoogleNewsSourceResolver — requests mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from agents.radar.google_news_source_resolver import GoogleNewsSourceResolver
from core.ports.source_resolver import ResolvedSource, SourceResolverError

_URL_GOOGLE = "https://news.google.com/rss/articles/CBMi123?oc=5"
_PAGINA_OK = (
    '<html><body><c-wiz><div jscontroller="x" data-n-a-sg="firma" '
    'data-n-a-ts="1700000000"></div></c-wiz></body></html>'
)
_RESPUESTA_OK = (
    r'[["wrb.fr","Fbv4je","[\"garturlres\",\"https://elpilon.com.co/noticia-real\",1]"]]'
)


def _response(text: str) -> MagicMock:
    response = MagicMock()
    response.text = text
    return response


def _patch_requests(get_return=None, post_return=None, get_side_effect=None):
    return (
        patch(
            "agents.radar.google_news_source_resolver.requests.get",
            return_value=get_return,
            side_effect=get_side_effect,
        ),
        patch("agents.radar.google_news_source_resolver.requests.post", return_value=post_return),
    )


def test_resolve_decodes_a_google_news_link() -> None:
    patch_get, patch_post = _patch_requests(_response(_PAGINA_OK), _response(_RESPUESTA_OK))

    with patch_get as mock_get, patch_post as mock_post:
        resultado = GoogleNewsSourceResolver().resolve(_URL_GOOGLE)

    assert resultado.success is True
    assert resultado.resolved_url == "https://elpilon.com.co/noticia-real"
    assert mock_get.call_args.args[0] == "https://news.google.com/rss/articles/CBMi123"
    assert "CBMi123" in mock_post.call_args.kwargs["data"]


def test_resolve_fails_when_the_page_has_no_signature() -> None:
    patch_get, patch_post = _patch_requests(_response("<html></html>"), _response(""))

    with patch_get, patch_post as mock_post:
        resultado = GoogleNewsSourceResolver().resolve(_URL_GOOGLE)

    assert resultado.success is False
    assert resultado.resolved_url is None
    assert resultado.error is not None
    mock_post.assert_not_called()


def test_resolve_fails_when_the_rpc_answer_has_no_url() -> None:
    patch_get, patch_post = _patch_requests(_response(_PAGINA_OK), _response("[]"))

    with patch_get, patch_post:
        resultado = GoogleNewsSourceResolver().resolve(_URL_GOOGLE)

    assert resultado.success is False
    assert resultado.resolved_url is None


@pytest.mark.parametrize("error", [requests.Timeout("lento"), requests.ConnectionError("caído")])
def test_resolve_reports_network_errors_as_a_failure_not_an_exception(error) -> None:
    patch_get, patch_post = _patch_requests(get_side_effect=error)

    with patch_get, patch_post:
        resultado = GoogleNewsSourceResolver().resolve(_URL_GOOGLE)

    assert resultado.success is False
    assert resultado.error is not None


def test_resolve_delegates_non_google_urls_to_the_fallback() -> None:
    fallback = MagicMock()
    fallback.resolve.return_value = ResolvedSource(success=True, resolved_url="https://x.com/a")

    resultado = GoogleNewsSourceResolver(fallback=fallback).resolve("https://bit.ly/abc")

    assert resultado.resolved_url == "https://x.com/a"
    fallback.resolve.assert_called_once_with("https://bit.ly/abc")


def test_resolve_fails_for_non_google_urls_without_a_fallback() -> None:
    resultado = GoogleNewsSourceResolver().resolve("https://bit.ly/abc")

    assert resultado.success is False


def test_resolve_rejects_an_empty_url() -> None:
    with pytest.raises(SourceResolverError):
        GoogleNewsSourceResolver().resolve("")
