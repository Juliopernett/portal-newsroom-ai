"""Real OpenRouter adapter for `core.ports.ai_provider.AIProvider`.

Sprint — configuración de proveedor de IA (2026-08-24). OpenRouter
(openrouter.ai) is an aggregator exposing many providers/models — including
several free or near-free ones — behind one OpenAI-compatible Chat
Completions endpoint. Wired as a selectable alternative to calling
Anthropic directly (see `core.entities.ai_configuracion`, Configuración →
IA), mainly for cost-free testing of `core.services.editorial_ai_service`
before committing real Anthropic API spend.

Uses `requests` directly — the same convention
`agents/wordpress/client.py`/`agents/meta_social/client.py` already use for
external HTTP integrations — not the `anthropic` SDK and not an OpenAI SDK
either: on the wire this is a single JSON POST, no client library earns its
keep for that.
"""

from __future__ import annotations

from typing import Any

import requests

from config.settings import Settings
from core.ports.ai_provider import AIProviderError

_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
_REQUEST_TIMEOUT_SECONDS = 60


class OpenRouterAIProvider:
    """`AIProvider` implemented against the OpenRouter Chat Completions API."""

    def __init__(self, settings: Settings, *, modelo: str) -> None:
        self._api_key = settings.openrouter_api_key
        self._modelo = modelo

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise AIProviderError(
                "OPENROUTER_API_KEY no está configurado en .env — la preparación "
                "editorial con IA no está disponible"
            )
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _completar(self, prompt: str, *, json_mode: bool) -> str:
        headers = self._headers()
        payload: dict[str, Any] = {
            "model": self._modelo,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = requests.post(
                _CHAT_COMPLETIONS_URL,
                headers=headers,
                json=payload,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise AIProviderError(f"error del proveedor de IA (OpenRouter): {exc}") from exc
        data = response.json()
        if "error" in data:
            raise AIProviderError(f"OpenRouter rechazó la solicitud: {data['error']}")
        try:
            contenido = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(
                f"respuesta de OpenRouter no tiene la forma esperada: {exc}"
            ) from exc
        return contenido or ""

    def generate(self, prompt: str) -> str:
        """Return the routed model's plain-text completion for `prompt`."""
        return self._completar(prompt, json_mode=False)

    def generate_structured(self, prompt: str, json_schema: dict[str, Any]) -> str:
        """Return the routed model's completion for `prompt`, requested as JSON.

        Uses `response_format: {"type": "json_object"}` — guarantees valid
        JSON syntax, not schema conformance (support for strict
        `json_schema` mode varies by the underlying routed model, unlike
        the Anthropic API). `core.services.editorial_ai_service` already
        validates the parsed shape regardless of provider, so this is
        sufficient defense in depth without depending on a feature not
        every OpenRouter-routed model implements.
        """
        return self._completar(prompt, json_mode=True)
