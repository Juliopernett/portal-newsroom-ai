"""Port for publishing content to a CMS.

Implemented by adapters for a specific CMS (WordPress today, potentially
another one later). Consumed by the future WordPress agent
(`agents/wordpress/`).

Per docs/PROJECT_RULES.md, this contract only exposes draft creation —
there is intentionally no `publish()` method. The system never publishes
automatically.

`create_draft` returns `CMSDraftResult` (post_id + url), not a bare
`str` — a Sprint 4A, Increment 3 change (see
docs/adr/ADR-006-multichannel-publication.md) from the original design,
which said this port would not need modifying. Building the real
WordPress adapter revealed `DestinoPublicacion` needs both `wp_post_id`
(for later status checks against the CMS) and `wp_url` (for reports and
links shared with clients) — a single opaque string could not carry
both. Zero adapters existed yet when this changed, so the change carries
no migration risk.
"""

from __future__ import annotations

from typing import Any, NamedTuple, Protocol


class CMSDraftResult(NamedTuple):
    """The identifier and URL of a draft just created in a CMS."""

    post_id: str
    url: str


class CMSPublisher(Protocol):
    """Contract for creating editorial drafts in a CMS.

    Implementations must never publish content directly; they only create
    drafts awaiting human review.
    """

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        """Create a draft in the CMS and return its post_id and url."""
        ...
