"""Domain entity: configuration of a single place Discovery Engine can scan.

A `Source` never fetches anything itself — it only records where a
`core.ports.content_source.ContentSource` adapter should look, whether it
is currently active, and how it should be weighted against other sources.

Sprint Fuentes (2026-10-29): sources are persisted and editable from the
Radar, so the scan knobs live here too — how often a source is due
(`intervalo_minutos`), how many entries and how old a candidate may be on
a scan (`max_items`/`max_age_days`, so a first scan never floods the
Radar), and the bookkeeping a cheap scan needs (`etag`/`last_modified`
for conditional requests, `last_error`/`errores_consecutivos` for backoff).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

_INTERVALO_MINIMO_MINUTOS = 5


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
    intervalo_minutos: int = 60
    max_items: int = 20
    max_age_days: int = 7
    last_error: str | None = None
    errores_consecutivos: int = 0
    etag: str | None = None
    last_modified: str | None = None
    last_new_count: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must not be empty")
        if not self.url:
            raise ValueError("url must not be empty")
        if self.priority < 0:
            raise ValueError(f"priority must not be negative, got {self.priority!r}")
        if self.intervalo_minutos < _INTERVALO_MINIMO_MINUTOS:
            raise ValueError(
                f"intervalo_minutos must be at least {_INTERVALO_MINIMO_MINUTOS}, "
                f"got {self.intervalo_minutos!r}"
            )
        if not 1 <= self.max_items <= 100:
            raise ValueError(f"max_items must be between 1 and 100, got {self.max_items!r}")
        if not 1 <= self.max_age_days <= 90:
            raise ValueError(f"max_age_days must be between 1 and 90, got {self.max_age_days!r}")
