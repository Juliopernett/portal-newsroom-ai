"""Real Anthropic adapter for `core.ports.ai_provider.AIProvider`.

Sprint 2026-08-21 — preparación editorial con IA. Uses the official
`anthropic` Python SDK against `claude-opus-5`, with adaptive thinking
left at its default (on) and `effort: "medium"` — a rewrite-and-structure
task, not one that needs the highest reasoning depth.

Unlike `agents.wordpress.client.WordPressCMSPublisher` and
`agents.meta_social.client.MetaGraphSocialMediaReader`, this adapter does
NOT raise at construction when unconfigured — see
`core.ports.ai_provider.AIProviderError`'s docstring for why: the system
must keep working (WordPress draft with raw text) even when the AI
provider is completely unavailable, so "not configured" has to look
exactly like any other transient failure to callers, not a startup error.
"""

from __future__ import annotations

from typing import Any

import anthropic

from config.settings import Settings
from core.ports.ai_provider import AIProviderError

_MODEL = "claude-opus-5"
_MAX_TOKENS = 8000


class AnthropicAIProvider:
    """`AIProvider` implemented against the real Anthropic API."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.anthropic_api_key

    def _client(self) -> anthropic.Anthropic:
        if not self._api_key:
            raise AIProviderError(
                "ANTHROPIC_API_KEY no está configurado en .env — la preparación "
                "editorial con IA no está disponible"
            )
        return anthropic.Anthropic(api_key=self._api_key)

    def generate(self, prompt: str) -> str:
        """Return Claude's plain-text completion for `prompt`."""
        try:
            response = self._client().messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                output_config={"effort": "medium"},
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise AIProviderError(f"error del proveedor de IA: {exc}") from exc
        if response.stop_reason == "refusal":
            raise AIProviderError("el proveedor de IA rechazó la solicitud")
        return next((b.text for b in response.content if b.type == "text"), "")

    def generate_structured(self, prompt: str, json_schema: dict[str, Any]) -> str:
        """Return Claude's completion for `prompt`, constrained to `json_schema`.

        Uses `output_config.format` — the response is guaranteed valid
        JSON conforming to the schema, no manual repair/retry needed.
        """
        try:
            response = self._client().messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                output_config={
                    "effort": "medium",
                    "format": {"type": "json_schema", "schema": json_schema},
                },
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise AIProviderError(f"error del proveedor de IA: {exc}") from exc
        if response.stop_reason == "refusal":
            raise AIProviderError("el proveedor de IA rechazó la solicitud")
        texto = next((b.text for b in response.content if b.type == "text"), None)
        if texto is None:
            raise AIProviderError("el proveedor de IA no devolvió contenido de texto")
        return texto
