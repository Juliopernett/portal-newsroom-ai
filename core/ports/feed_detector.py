"""Port for finding the RSS/Atom feed behind a website URL.

Sprint Fuentes (2026-10-29). The operator pastes a site address
(`https://www.blogvallenato.com`) or a feed address; the adapter works out
which feed to subscribe to and returns its first entries so the UI can show
"this is what you would get" before the source is saved.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class FeedDetectorError(ValueError):
    """The URL cannot be inspected (invalid, not public, unreachable)."""


@dataclass(frozen=True, slots=True)
class EntradaFeed:
    """One entry of a detected feed, enough to preview it."""

    titulo: str
    publicada: datetime | None


@dataclass(frozen=True, slots=True)
class FeedDetectado:
    """A feed found for a URL, with its first entries."""

    feed_url: str
    titulo: str
    entradas: tuple[EntradaFeed, ...]


class FeedDetector(Protocol):
    """Contract for discovering the feed behind a URL."""

    def detectar(self, url: str) -> FeedDetectado | None:
        """Return the feed for `url`, or `None` if the site exposes no usable feed.

        Raises `FeedDetectorError` if `url` cannot be inspected at all.
        """
        ...
