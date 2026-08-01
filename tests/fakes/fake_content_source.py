"""Test double for `core.ports.content_source.ContentSource`.

Reads a JSON fixture file instead of the network so `DiscoveryEngine` (and
anything built on top of it) can be exercised end to end without internet
access, a scraping library, or a real source. See tests/fixtures/ for the
JSON files this reads.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any  # raw JSON values are inherently untyped
from uuid import uuid4

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source
from core.services.deduplication import generate_candidate_hash


class FakeContentSource:
    """A `ContentSource` backed by a JSON fixture file on disk.

    Each entry in the fixture becomes one `NewsCandidate`, tagged with the
    configured `source` and fingerprinted the same way a real adapter
    would via `core.services.deduplication.generate_candidate_hash`.
    """

    def __init__(
        self,
        source: Source,
        fixture_path: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._source = source
        self._fixture_path = fixture_path
        self._clock = clock

    @property
    def source(self) -> Source:
        return self._source

    def fetch_candidates(self) -> list[NewsCandidate]:
        """Read the fixture file and return one `NewsCandidate` per entry."""
        raw_items: list[dict[str, Any]] = json.loads(
            self._fixture_path.read_text(encoding="utf-8")
        )
        return [self._build_candidate(item) for item in raw_items]

    def _build_candidate(self, item: dict[str, Any]) -> NewsCandidate:
        published_at_raw = item.get("published_at")
        metadata = {"category": item["category"]} if "category" in item else {}
        return NewsCandidate(
            id=str(uuid4()),
            source=self._source.id,
            title=item["title"],
            url=item["url"],
            summary=item["summary"],
            image_url=item.get("image_url"),
            published_at=datetime.fromisoformat(published_at_raw) if published_at_raw else None,
            discovered_at=self._clock(),
            hash=generate_candidate_hash(source=self._source.id, url=item["url"]),
            metadata=metadata,
            confidence=float(item.get("confidence", 1.0)),
        )
