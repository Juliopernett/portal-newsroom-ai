"""Domain events.

This package will hold the events the domain raises as content moves
through the editorial pipeline (news detected, article rewritten, draft
created, notification requested, ...).

Sprint 2+ will give these events real payloads once the agent that raises
each one is implemented. No publish/subscribe mechanism (event bus) exists
yet on purpose — see docs/ARCHITECTURE.md, section "Eventos de dominio".

Every event module defines one class named after the event, in past tense
(it describes something that already happened). Re-exported here so
consumers can `from core.events import NewsFound` instead of reaching into
the submodule.
"""

from __future__ import annotations

from core.events.article_rewritten import ArticleRewritten
from core.events.draft_created import DraftCreated
from core.events.news_found import NewsFound
from core.events.notification_requested import NotificationRequested

__all__ = [
    "ArticleRewritten",
    "DraftCreated",
    "NewsFound",
    "NotificationRequested",
]
