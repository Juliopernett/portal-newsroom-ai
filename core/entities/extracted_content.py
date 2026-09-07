"""Domain entity: structured content pulled from a NewsCandidate's original source.

Produced by a `core.ports.content_extractor.ContentExtractor` once a
`NewsCandidate`'s Google News URL has been resolved to the real source
(`core.services.source_resolution_service`). This is the "materia prima"
handed to a future Writer agent (Discovery 4+) — nothing here is
rewritten or generated, only extracted as-is from the original page.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtractedContent:
    """Structured content extracted from a real article page.

    `source_url` is the real, resolved URL this content was extracted
    from (never the Google News discovery URL). `author`/`published_at`/
    `site_name`/`image_urls` are best-effort — not every page exposes
    them, so they are optional rather than forcing an extractor to
    fabricate a value.
    """

    title: str
    body: str
    source_url: str
    author: str | None = None
    published_at: datetime | None = None
    site_name: str | None = None
    image_urls: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("title must not be empty")
        if not self.body:
            raise ValueError("body must not be empty")
        if not self.source_url:
            raise ValueError("source_url must not be empty")
