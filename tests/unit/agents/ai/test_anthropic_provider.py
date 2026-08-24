"""Unit tests for AnthropicAIProvider — anthropic.Anthropic mocked, no network."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import anthropic
import pytest

from agents.ai.anthropic_provider import AnthropicAIProvider
from config.settings import Settings
from core.ports.ai_provider import AIProviderError


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {"anthropic_api_key": "sk-ant-test-key"}
    defaults.update(overrides)
    return Settings(**defaults)


def _text_response(text: str, stop_reason: str = "end_turn") -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.stop_reason = stop_reason
    return response


def test_generate_raises_when_api_key_is_missing() -> None:
    provider = AnthropicAIProvider(_settings(anthropic_api_key=None))

    with pytest.raises(AIProviderError, match="ANTHROPIC_API_KEY"):
        provider.generate("hola")


def test_generate_structured_raises_when_api_key_is_missing() -> None:
    provider = AnthropicAIProvider(_settings(anthropic_api_key=None))

    with pytest.raises(AIProviderError, match="ANTHROPIC_API_KEY"):
        provider.generate_structured("hola", {"type": "object"})


def test_generate_does_not_raise_at_construction_when_unconfigured() -> None:
    # unlike WordPressCMSPublisher/MetaGraphSocialMediaReader, construction
    # itself must never fail — see core.ports.ai_provider.AIProviderError
    AnthropicAIProvider(_settings(anthropic_api_key=None))


def test_generate_returns_the_text_block() -> None:
    provider = AnthropicAIProvider(_settings())
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _text_response("respuesta del modelo")

    with patch("agents.ai.anthropic_provider.anthropic.Anthropic", return_value=mock_client):
        resultado = provider.generate("hola")

    assert resultado == "respuesta del modelo"


def test_generate_uses_claude_opus_5() -> None:
    provider = AnthropicAIProvider(_settings())
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _text_response("ok")

    with patch("agents.ai.anthropic_provider.anthropic.Anthropic", return_value=mock_client):
        provider.generate("hola")

    _args, kwargs = mock_client.messages.create.call_args
    assert kwargs["model"] == "claude-opus-5"


def test_generate_raises_on_refusal() -> None:
    provider = AnthropicAIProvider(_settings())
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _text_response("", stop_reason="refusal")

    with patch("agents.ai.anthropic_provider.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(AIProviderError, match="rechazó"):
            provider.generate("hola")


def test_generate_wraps_an_api_error() -> None:
    provider = AnthropicAIProvider(_settings())
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())

    with patch("agents.ai.anthropic_provider.anthropic.Anthropic", return_value=mock_client):
        with pytest.raises(AIProviderError):
            provider.generate("hola")


def test_generate_structured_passes_the_schema_via_output_config() -> None:
    provider = AnthropicAIProvider(_settings())
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _text_response('{"titulo": "T"}')
    schema = {"type": "object", "properties": {"titulo": {"type": "string"}}}

    with patch("agents.ai.anthropic_provider.anthropic.Anthropic", return_value=mock_client):
        resultado = provider.generate_structured("hola", schema)

    assert resultado == '{"titulo": "T"}'
    _args, kwargs = mock_client.messages.create.call_args
    assert kwargs["output_config"]["format"] == {"type": "json_schema", "schema": schema}
