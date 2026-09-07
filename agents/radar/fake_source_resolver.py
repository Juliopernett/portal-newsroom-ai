"""Canned `SourceResolver` — stands in for tests, no network.

Same discipline as `agents.ai.fake_provider.FakeAIProvider`: a canned
successful resolution by default, with constructor overrides so a test
can force a failure instead. `tests/integration/api/conftest.py` wires
the zero-argument form as the default for every test via
`app.dependency_overrides`.
"""

from __future__ import annotations

from core.ports.source_resolver import ResolvedSource

_URL_RESUELTA_DEMO = "https://example.com/[DEMO]-fuente-original"


class FakeSourceResolver:
    """`SourceResolver` backed by a fixed, clearly-marked demo result (or a forced failure)."""

    def __init__(self, *, resultado: ResolvedSource | None = None) -> None:
        self._resultado = resultado

    def resolve(self, url: str) -> ResolvedSource:
        if self._resultado is not None:
            return self._resultado
        return ResolvedSource(success=True, resolved_url=_URL_RESUELTA_DEMO, error=None)
