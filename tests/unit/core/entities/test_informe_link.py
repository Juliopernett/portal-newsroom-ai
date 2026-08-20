"""Unit tests for the InformeLink entity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.entities.informe_link import InformeLink


def _build(**overrides: object) -> InformeLink:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "pauta_id": "pauta-1",
        "token_hash": "abc123",
        "created_at": now,
        "expires_at": now + timedelta(days=15),
    }
    defaults.update(overrides)
    return InformeLink(**defaults)


def test_create_informe_link_assigns_defaults() -> None:
    link = _build()

    assert link.id


def test_create_informe_link_rejects_empty_pauta_id() -> None:
    with pytest.raises(ValueError, match="pauta_id"):
        _build(pauta_id="")


def test_create_informe_link_rejects_empty_token_hash() -> None:
    with pytest.raises(ValueError, match="token_hash"):
        _build(token_hash="")


@pytest.mark.parametrize("delta", [timedelta(0), timedelta(days=-1)])
def test_create_informe_link_rejects_expires_at_not_after_created_at(delta: timedelta) -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="expires_at"):
        _build(created_at=now, expires_at=now + delta)


def test_informe_link_is_immutable() -> None:
    link = _build()

    with pytest.raises(AttributeError):
        link.token_hash = "other"  # type: ignore[misc]
