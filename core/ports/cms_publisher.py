"""Port for publishing content to a CMS.

Implemented by adapters for a specific CMS (WordPress today, potentially
another one later). Consumed by the future WordPress agent
(`agents/wordpress/`).

Per docs/PROJECT_RULES.md, this contract only exposes draft creation —
there is intentionally no `publish()` method. The system never publishes
automatically.
"""

from __future__ import annotations

from typing import Any, Protocol


class CMSPublisher(Protocol):
    """Contract for creating editorial drafts in a CMS.

    Implementations must never publish content directly; they only create
    drafts awaiting human review.
    """

    def create_draft(self, content: dict[str, Any]) -> str:
        """Create a draft in the CMS and return its identifier or URL."""
        ...
