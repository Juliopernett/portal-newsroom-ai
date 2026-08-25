"""Real `ContentSource` adapter reading an RSS/Atom feed.

Sprint Discovery 1 (2026-08-25) — the first real `ContentSource` this
project has (see `agents/radar/README.md`). Fetches over HTTP with
`requests` and parses with `feedparser` (handles both RSS and Atom), then
maps each feed entry to `core.entities.news_candidate.NewsCandidate`.
Deliberately minimal: an entry missing `title` or `link` is skipped (with
a warning) rather than failing the whole fetch — a real-world RSS feed
occasionally has a malformed entry, and one bad entry should never hide
every other real one.
"""

from __future__ import annotations

from datetime import UTC, datetime
from time import struct_time

import feedparser
import requests

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source
from core.ports.content_source import ContentSourceError
from core.services.deduplication import generate_candidate_hash
from shared.logger import get_logger

logger = get_logger(__name__)

_REQUEST_TIMEOUT_SECONDS = 15


class RssContentSource:
    """`ContentSource` implemented against a real RSS/Atom feed URL."""

    def __init__(self, source: Source, *, timeout: int = _REQUEST_TIMEOUT_SECONDS) -> None:
        self._source = source
        self._timeout = timeout

    @property
    def source(self) -> Source:
        return self._source

    def fetch_candidates(self) -> list[NewsCandidate]:
        """Fetch and parse the feed, returning one `NewsCandidate` per usable entry.

        Raises `ContentSourceError` if the feed can't be reached (network
        failure, non-2xx response) or can't be parsed at all (malformed
        XML with zero usable entries) — never a raw `requests`/
        `feedparser` exception, so callers only ever need to know about
        this one domain-level error.
        """
        try:
            response = requests.get(self._source.url, timeout=self._timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ContentSourceError(
                f"No se pudo obtener el feed '{self._source.name}': {exc}"
            ) from exc

        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise ContentSourceError(
                f"El feed '{self._source.name}' no se pudo interpretar: {parsed.get('bozo_exception')}"
            )

        candidatos: list[NewsCandidate] = []
        for entry in parsed.entries:
            candidato = self._build_candidate(entry)
            if candidato is not None:
                candidatos.append(candidato)
        return candidatos

    def _build_candidate(self, entry: feedparser.FeedParserDict) -> NewsCandidate | None:
        title = entry.get("title")
        url = entry.get("link")
        if not title or not url:
            logger.warning(
                "Descartando entrada incompleta (sin título o enlace) de '%s'", self._source.name
            )
            return None

        metadata: dict[str, str] = {}
        guid = entry.get("id")
        if guid:
            metadata["guid"] = guid

        return NewsCandidate(
            source=self._source.id,
            title=title,
            url=url,
            summary=entry.get("summary", ""),
            published_at=_parse_published_at(entry.get("published_parsed")),
            hash=generate_candidate_hash(source=self._source.id, url=url),
            metadata=metadata,
        )


def _parse_published_at(published_parsed: struct_time | None) -> datetime | None:
    if published_parsed is None:
        return None
    return datetime(*published_parsed[:6], tzinfo=UTC)
