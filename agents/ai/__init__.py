"""AI text-generation adapters.

`anthropic_provider.AnthropicAIProvider` is what `app.api.dependencies.
get_ai_provider` returns — wraps the Anthropic Python SDK against
`ANTHROPIC_API_KEY`, configured 2026-08-21 for the editorial-preparation
sprint (`core.services.editorial_ai_service`). `fake_provider.FakeAIProvider`
is what tests use instead, via `app.dependency_overrides` — nothing in
production code should construct either adapter directly.
"""
