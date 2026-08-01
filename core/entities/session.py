"""Domain entity: a logged-in session for a User.

Server-side, stored in Postgres — not a signed/stateless token (JWT).
A stolen device's session can be revoked instantly by deleting this row;
a stateless token can't be revoked without a denylist, which is this same
table by another name. `token_hash` is never the raw token a browser
holds in its cookie — see `core.ports.session_repository.SessionRepository`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class Session:
    """A single logged-in session, valid until `expires_at`."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str
    token_hash: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime

    def __post_init__(self) -> None:
        if not self.user_id:
            raise ValueError("user_id must not be empty")
        if not self.token_hash:
            raise ValueError("token_hash must not be empty")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
