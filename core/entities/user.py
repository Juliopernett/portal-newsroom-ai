"""Domain entity: a Portal Vallenato team member who can log into the system.

Not `Client` (a commercial customer) and not the future conceptual
`MediaOutlet` (a platform tenant) — a third, distinct "who" in this
codebase: the person operating the system. Scoped deliberately minimal
(MVP login sprint): no roles, no active/inactive flag, no lockout
counters — see docs/adr/ADR-005-authentication.md for what was left out
and why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class User:
    """A team member authorized to operate Portal Newsroom AI."""

    id: str = field(default_factory=lambda: str(uuid4()))
    email: str
    password_hash: str
    nombre: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.email or "@" not in self.email:
            raise ValueError(f"email must be a valid-looking address, got {self.email!r}")
        if not self.password_hash:
            raise ValueError("password_hash must not be empty")
        if not self.nombre:
            raise ValueError("nombre must not be empty")
