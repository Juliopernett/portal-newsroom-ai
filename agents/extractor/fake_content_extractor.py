"""Canned `ContentExtractor` — stands in for tests, no network.

Same discipline as `agents.ai.fake_provider.FakeAIProvider`: every
generated value is prefixed `[DEMO]`, and a caller can force a
`ContentExtractorError` instead of the canned success.
`tests/integration/api/conftest.py` wires the zero-argument form as the
default for every test via `app.dependency_overrides`.
"""

from __future__ import annotations

from core.entities.extracted_content import ExtractedContent
from core.ports.content_extractor import ContentExtractorError


class FakeContentExtractor:
    """`ContentExtractor` backed by fixed, clearly-marked demo data (or a forced error)."""

    def __init__(self, *, error: ContentExtractorError | None = None) -> None:
        self._error = error

    def extract(self, reference: str) -> ExtractedContent:
        if self._error is not None:
            raise self._error
        return ExtractedContent(
            title="[DEMO] Titular extraído",
            body="[DEMO] Cuerpo extraído del artículo original.",
            source_url=reference,
            author="[DEMO] Autor",
            site_name="[DEMO] Medio",
        )
