"""Unit tests for the Session entity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.entities.session import Session


def _build(**overrides: object) -> Session:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "user_id": "user-1",
        "token_hash": "abc123",
        "created_at": now,
        "expires_at": now + timedelta(days=7),
    }
    defaults.update(overrides)
    return Session(**defaults)


def test_create_session_assigns_defaults() -> None:
    session = _build()

    assert session.id


def test_create_session_rejects_empty_user_id() -> None:
    with pytest.raises(ValueError, match="user_id"):
        _build(user_id="")


def test_create_session_rejects_empty_token_hash() -> None:
    with pytest.raises(ValueError, match="token_hash"):
        _build(token_hash="")


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(days=-1)])
def test_create_session_rejects_expires_at_not_after_created_at(delta: timedelta) -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="expires_at"):
        _build(created_at=now, expires_at=now + delta)


def test_session_is_immutable() -> None:
    session = _build()

    with pytest.raises(AttributeError):
        session.token_hash = "other"  # type: ignore[misc]
