"""Domain event: a new, non-duplicate piece of content was detected.

Not implemented yet. Payload (reference, source, detected_at, ...) will be
defined in Sprint 2 alongside `agents/radar/`, once the concrete data it
needs to carry is known — see docs/ROADMAP.md.
"""

from __future__ import annotations


class NewsFound:
    """Raised by the future Radar agent when it finds new content."""
