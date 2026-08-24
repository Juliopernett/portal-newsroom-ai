"""Port for AI text generation providers.

Implemented by adapters wrapping a concrete LLM provider (OpenAI,
Anthropic, ...). Consumed by the future Writer, SEO, Social and AI
Orchestrator agents — and, since Sprint 2026-08-21, by
`core.services.editorial_ai_service` for the commercial pillar's WordPress
editorial rewrite. None of those agents should import an LLM SDK directly
— they depend on this contract, so the provider can change without
touching agent code.
"""

from __future__ import annotations

from typing import Any, Protocol


class AIProviderError(RuntimeError):
    """Raised for any AI provider failure: not configured, network/API
    error, or a refused/unusable response.

    Deliberately one exception type for all of these — unlike
    `agents.wordpress.client.WordPressConfigurationError` (which fails
    fast at construction and becomes a 503 via `app.api.errors`), a
    missing/invalid AI configuration must be handled the same way a
    transient outage is: callers that need the system to keep working
    without AI (see `core.services.editorial_ai_service`) catch this one
    type and degrade gracefully, they never see a 503.
    """


class AIProvider(Protocol):
    """Contract for generating text from a prompt."""

    def generate(self, prompt: str) -> str:
        """Return the model's completion for `prompt`."""
        ...

    def generate_structured(self, prompt: str, json_schema: dict[str, Any]) -> str:
        """Return the model's completion for `prompt`, constrained to `json_schema`.

        The returned string is guaranteed valid JSON conforming to
        `json_schema` — callers still validate it (defense in depth), but
        never need to repair or re-request malformed JSON. Raises
        `AIProviderError` if the provider is not configured, unreachable,
        or refuses the request.
        """
        ...
