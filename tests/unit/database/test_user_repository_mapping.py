"""Unit test for the tz-aware branch of User's DB-to-domain mapping.

SQLite always drops tzinfo on round trip (see
`database/repositories/user_repository.py`), so no SQLite-backed
integration test ever exercises the branch where the stored value already
carries tzinfo — the branch a real PostgreSQL/Railway database takes.
Tested directly against the mapping function instead of a live database,
since that's a pure, DB-agnostic function.
"""

from __future__ import annotations

from datetime import UTC, datetime

from database.models.user import UserModel
from database.repositories.user_repository import _to_domain


def test_to_domain_keeps_an_already_timezone_aware_created_at() -> None:
    created_at = datetime(2026, 7, 30, 9, 0, tzinfo=UTC)
    model = UserModel(
        id="user-1",
        email="editor@portalvallenato.com",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fake",
        nombre="Editor de Turno",
        created_at=created_at,
    )

    user = _to_domain(model)

    assert user.created_at == created_at
    assert user.created_at.tzinfo is UTC
