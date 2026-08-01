"""Domain entity: an article as it exists in the editorial pipeline.

Produced once a `NewsCandidate` has been extracted and rewritten; modeled
here purely as data — the agents that create and transform it (Writer,
SEO, Images, WordPress) are not implemented yet (see docs/ROADMAP.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class ArticleStatus(StrEnum):
    """Where an article is in the editorial approval flow.

    `PUBLISHED` records that a human published it elsewhere (WordPress) —
    the system itself never performs that action, see
    docs/PROJECT_RULES.md, rule 1.
    """

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


@dataclass(frozen=True, slots=True, kw_only=True)
class Article:
    """An article moving through the editorial pipeline."""

    id: str = field(default_factory=lambda: str(uuid4()))
    title: str
    body: str
    featured_image: str | None = None
    category: str | None = None
    tags: tuple[str, ...] = ()
    source: str
    status: ArticleStatus = ArticleStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.title:
            raise ValueError("title must not be empty")
        if not self.source:
            raise ValueError("source must not be empty")
