"""Domain entity: an actionable task assigned to the editorial team.

Represents work the system is asking a human to do (review a draft,
approve a translation, ...) — never work the system performs itself, see
docs/PROJECT_RULES.md, rule 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class EditorialTaskStatus(StrEnum):
    """Lifecycle of an editorial task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True, kw_only=True)
class EditorialTask:
    """A unit of editorial work tracked against a single article."""

    id: str = field(default_factory=lambda: str(uuid4()))
    article_id: str
    assigned_to: str | None = None
    priority: int = 0
    status: EditorialTaskStatus = EditorialTaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.article_id:
            raise ValueError("article_id must not be empty")
        if self.priority < 0:
            raise ValueError(f"priority must not be negative, got {self.priority!r}")
