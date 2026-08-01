"""Port for image handling.

Implemented by adapters that download, store and serve images associated
with an article. Consumed by the future Images agent (`agents/images/`).
"""

from __future__ import annotations

from typing import Protocol


class ImageProvider(Protocol):
    """Contract for fetching and persisting an image from a source URL."""

    def store_from_url(self, url: str) -> str:
        """Download the image at `url` and return its local/stored path."""
        ...
