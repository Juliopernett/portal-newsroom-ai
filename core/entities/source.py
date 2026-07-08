"""Domain entity: configuration of a single place Discovery Engine can scan.

A `Source` never fetches anything itself — it only records where a
`core.ports.content_source.ContentSource` adapter should look, whether it
is currently active, and how it should be weighted against other sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class Source:
    """A configured place Discovery Engine can request candidates from."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str
    type: str
    url: str
    enabled: bool = True
    priority: int = 0
    last_scan: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.url:
            raise ValueError("url must not be empty")
        if self.priority < 0:
            raise ValueError(f"priority must not be negative, got {self.priority!r}")
