"""Unit tests for the Source entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.source import Source


def _build(**overrides: object) -> Source:
    defaults: dict[str, object] = {
        "name": "Vallenato Hoy",
        "type": "rss",
        "url": "https://vallenatohoy.example.com/feed",
    }
    defaults.update(overrides)
    return Source(**defaults)


def test_create_source_assigns_defaults() -> None:
    source = _build()

    assert source.id
    assert source.enabled is True
    assert source.priority == 0
    assert source.last_scan is None


def test_create_source_accepts_explicit_values() -> None:
    last_scan = datetime(2026, 7, 1, tzinfo=UTC)

    source = _build(id="source-1", enabled=False, priority=5, last_scan=last_scan)

    assert source.id == "source-1"
    assert source.enabled is False
    assert source.priority == 5
    assert source.last_scan == last_scan


def test_create_source_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name"):
        _build(name="")


def test_create_source_rejects_empty_url() -> None:
    with pytest.raises(ValueError, match="url"):
        _build(url="")


def test_create_source_rejects_negative_priority() -> None:
    with pytest.raises(ValueError, match="priority"):
        _build(priority=-1)
