"""Unit tests for the ExtractedContent entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.extracted_content import ExtractedContent


def _build(**overrides: object) -> ExtractedContent:
    defaults: dict[str, object] = {
        "title": "Un festival vallenato bate récord de asistencia",
        "body": "Miles de personas asistieron a la clausura del festival.",
        "source_url": "https://elpilon.com.co/festival-record",
    }
    defaults.update(overrides)
    return ExtractedContent(**defaults)


def test_create_extracted_content_assigns_defaults() -> None:
    content = _build()

    assert content.author is None
    assert content.published_at is None
    assert content.site_name is None
    assert content.image_urls == ()


def test_create_extracted_content_accepts_explicit_values() -> None:
    published_at = datetime(2026, 8, 20, tzinfo=UTC)

    content = _build(
        author="Redacción El Pilón",
        published_at=published_at,
        site_name="El Pilón",
        image_urls=("https://elpilon.com.co/img/festival.jpg",),
    )

    assert content.author == "Redacción El Pilón"
    assert content.published_at == published_at
    assert content.site_name == "El Pilón"
    assert content.image_urls == ("https://elpilon.com.co/img/festival.jpg",)


@pytest.mark.parametrize("field_name", ["title", "body", "source_url"])
def test_create_extracted_content_rejects_empty_required_fields(field_name: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        _build(**{field_name: ""})


def test_extracted_content_is_immutable() -> None:
    content = _build()

    with pytest.raises(AttributeError):
        content.title = "Otro título"  # type: ignore[misc]
