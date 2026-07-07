"""Domain event: an editorial draft was created in the CMS.

Not implemented yet. Will be defined together with `agents/wordpress/` —
see docs/ROADMAP.md.

Reminder: this event marks a draft awaiting human review, never a
publication — see docs/PROJECT_RULES.md, rule 1.
"""

from __future__ import annotations


class DraftCreated:
    """Raised by the future WordPress agent when a draft is created."""
