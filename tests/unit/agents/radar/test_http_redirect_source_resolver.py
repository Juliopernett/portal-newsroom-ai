"""Unit tests for HttpRedirectSourceResolver — requests.get mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from agents.radar.http_redirect_source_resolver import HttpRedirectSourceResolver
from core.ports.source_resolver import SourceResolverError

_URL_DESCUBRIMIENTO = "https://news.google.com/rss/articles/CBMi123"


def _mock_response(final_url: str, status_ok: bool = True) -> MagicMock:
    response = MagicMock()
    response.url = final_url
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    if not status_ok:
        response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    return response


def test_resolve_follows_a_redirect_to_a_different_host() -> None:
    resolver = HttpRedirectSourceResolver()

    with patch(
        "agents.radar.http_redirect_source_resolver.requests.get",
        return_value=_mock_response("https://elpilon.com.co/noticia-real"),
    ) as mock_get:
        resultado = resolver.resolve(_URL_DESCUBRIMIENTO)

    assert resultado.success is True
    assert resultado.resolved_url == "https://elpilon.com.co/noticia-real"
    assert resultado.error is None
    args, kwargs = mock_get.call_args
    assert args[0] == _URL_DESCUBRIMIENTO
    assert kwargs["allow_redirects"] is True
    assert kwargs["timeout"] == 15


def test_resolve_treats_no_real_redirect_as_a_failure() -> None:
    """Same host in and out — likely a JS redirect this resolver can't follow."""
    resolver = HttpRedirectSourceResolver()

    with patch(
        "agents.radar.http_redirect_source_resolver.requests.get",
        return_value=_mock_response(_URL_DESCUBRIMIENTO),
    ):
        resultado = resolver.resolve(_URL_DESCUBRIMIENTO)

    assert resultado.success is False
    assert resultado.resolved_url is None
    assert resultado.error is not None


def test_resolve_reports_a_timeout_as_a_failure_not_an_exception() -> None:
    resolver = HttpRedirectSourceResolver()

    with patch(
        "agents.radar.http_redirect_source_resolver.requests.get",
        side_effect=requests.Timeout("tardó demasiado"),
    ):
        resultado = resolver.resolve(_URL_DESCUBRIMIENTO)

    assert resultado.success is False
    assert resultado.resolved_url is None
    assert resultado.error is not None


def test_resolve_reports_a_redirect_loop_as_a_failure_not_an_exception() -> None:
    resolver = HttpRedirectSourceResolver()

    with patch(
        "agents.radar.http_redirect_source_resolver.requests.get",
        side_effect=requests.TooManyRedirects("ciclo de redirects"),
    ):
        resultado = resolver.resolve(_URL_DESCUBRIMIENTO)

    assert resultado.success is False
    assert resultado.resolved_url is None
    assert "redirect" in (resultado.error or "").lower()


def test_resolve_reports_a_connection_error_as_a_failure_not_an_exception() -> None:
    resolver = HttpRedirectSourceResolver()

    with patch(
        "agents.radar.http_redirect_source_resolver.requests.get",
        side_effect=requests.ConnectionError("no se pudo conectar"),
    ):
        resultado = resolver.resolve(_URL_DESCUBRIMIENTO)

    assert resultado.success is False
    assert resultado.resolved_url is None


def test_resolve_reports_a_non_2xx_response_as_a_failure_not_an_exception() -> None:
    resolver = HttpRedirectSourceResolver()

    with patch(
        "agents.radar.http_redirect_source_resolver.requests.get",
        return_value=_mock_response(_URL_DESCUBRIMIENTO, status_ok=False),
    ):
        resultado = resolver.resolve(_URL_DESCUBRIMIENTO)

    assert resultado.success is False
    assert resultado.resolved_url is None


def test_resolve_rejects_an_empty_url() -> None:
    resolver = HttpRedirectSourceResolver()

    with pytest.raises(SourceResolverError):
        resolver.resolve("")
