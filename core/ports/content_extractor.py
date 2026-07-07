"""Port for content extraction.

Implemented by adapters that fetch a full article's content and metadata
from a reference (typically a URL), using tools such as Playwright,
BeautifulSoup or Requests. Consumed by the future Extractor agent
(`agents/extractor/`).
"""

from __future__ import annotations

from typing import Any, Protocol


class ContentExtractor(Protocol):
    """Contract for turning a content reference into structured data.

    The concrete return shape (title, body, images, metadata, ...) will be
    formalized as a domain entity in `core/entities/` once the Extractor
    agent is implemented (see docs/ROADMAP.md). Until then, adapters
    return a plain mapping to avoid guessing the domain model prematurely.
    """

    def extract(self, reference: str) -> dict[str, Any]:
        """Fetch and structure the content identified by `reference`."""
        ...
