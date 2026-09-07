"""Port for content extraction.

Implemented by adapters that fetch a full article's content and metadata
from a reference (typically a resolved article URL — see
`core.ports.source_resolver.SourceResolver`), using tools such as
BeautifulSoup or Requests. Consumed by `core.services
.source_resolution_service` on behalf of the Extractor agent
(`agents/extractor/`).
"""

from __future__ import annotations

from typing import Protocol

from core.entities.extracted_content import ExtractedContent


class ContentExtractorError(RuntimeError):
    """Raised when a `ContentExtractor` adapter cannot extract usable content.

    Covers network failure, a non-2xx response, a timeout, or a page with
    no recognizable article content (e.g. one that requires JavaScript to
    render) — same role `ContentSourceError` plays for
    `core.ports.content_source`, so a caller only needs to catch one
    domain-level exception regardless of which HTTP/parsing library the
    concrete adapter uses.
    """


class ContentExtractor(Protocol):
    """Contract for turning a content reference into structured data."""

    def extract(self, reference: str) -> ExtractedContent:
        """Fetch and structure the content identified by `reference`.

        Raises `ContentExtractorError` if `reference` cannot be fetched
        or no usable article content can be found on the page.
        """
        ...
