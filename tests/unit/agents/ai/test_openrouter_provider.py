"""Unit tests for OpenRouterAIProvider — requests.post mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from agents.ai.openrouter_provider import OpenRouterAIProvider
from config.settings import Settings
from core.ports.ai_provider import AIProviderError


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {"openrouter_api_key": "sk-or-test-key"}
    defaults.update(overrides)
    return Settings(**defaults)


def _response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = {"choices": [{"message": {"content": content}}]}
    return mock


def test_generate_raises_when_api_key_is_missing() -> None:
    provider = OpenRouterAIProvider(_settings(openrouter_api_key=None), modelo="deepseek/deepseek-chat")

    with pytest.raises(AIProviderError, match="OPENROUTER_API_KEY"):
        provider.generate("hola")


def test_generate_does_not_raise_at_construction_when_unconfigured() -> None:
    OpenRouterAIProvider(_settings(openrouter_api_key=None), modelo="deepseek/deepseek-chat")


def test_generate_returns_the_message_content() -> None:
    provider = OpenRouterAIProvider(_settings(), modelo="deepseek/deepseek-chat")

    with patch(
        "agents.ai.openrouter_provider.requests.post", return_value=_response("respuesta del modelo")
    ):
        resultado = provider.generate("hola")

    assert resultado == "respuesta del modelo"


def test_generate_sends_the_configured_model_and_bearer_token() -> None:
    provider = OpenRouterAIProvider(_settings(), modelo="deepseek/deepseek-chat")

    with patch(
        "agents.ai.openrouter_provider.requests.post", return_value=_response("ok")
    ) as mock_post:
        provider.generate("hola")

    _args, kwargs = mock_post.call_args
    assert kwargs["json"]["model"] == "deepseek/deepseek-chat"
    assert kwargs["headers"]["Authorization"] == "Bearer sk-or-test-key"


def test_generate_structured_requests_json_object_response_format() -> None:
    provider = OpenRouterAIProvider(_settings(), modelo="deepseek/deepseek-chat")

    with patch(
        "agents.ai.openrouter_provider.requests.post", return_value=_response('{"a": 1}')
    ) as mock_post:
        resultado = provider.generate_structured("hola", {"type": "object"})

    assert resultado == '{"a": 1}'
    _args, kwargs = mock_post.call_args
    assert kwargs["json"]["response_format"] == {"type": "json_object"}


def test_generate_wraps_a_connection_error() -> None:
    provider = OpenRouterAIProvider(_settings(), modelo="deepseek/deepseek-chat")

    with patch(
        "agents.ai.openrouter_provider.requests.post",
        side_effect=requests.ConnectionError("no responde"),
    ):
        with pytest.raises(AIProviderError):
            provider.generate("hola")


def test_generate_raises_when_openrouter_returns_an_error_payload() -> None:
    provider = OpenRouterAIProvider(_settings(), modelo="deepseek/deepseek-chat")
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": {"message": "invalid model"}}

    with patch("agents.ai.openrouter_provider.requests.post", return_value=mock_response):
        with pytest.raises(AIProviderError, match="rechazó"):
            provider.generate("hola")


def test_generate_raises_on_a_malformed_success_response() -> None:
    provider = OpenRouterAIProvider(_settings(), modelo="deepseek/deepseek-chat")
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": []}

    with patch("agents.ai.openrouter_provider.requests.post", return_value=mock_response):
        with pytest.raises(AIProviderError, match="forma esperada"):
            provider.generate("hola")
