"""Port for AI text generation providers.

Implemented by adapters wrapping a concrete LLM provider (OpenAI,
Anthropic, ...). Consumed by the future Writer, SEO, Social and AI
Orchestrator agents. None of those agents should import an LLM SDK
directly — they depend on this contract, so the provider can change
without touching agent code.
"""

from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    """Contract for generating text from a prompt."""

    def generate(self, prompt: str) -> str:
        """Return the model's completion for `prompt`."""
        ...
