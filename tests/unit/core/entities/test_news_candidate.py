"""Unit tests for the NewsCandidate entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.news_candidate import NewsCandidate


def _build(**overrides: object) -> NewsCandidate:
    defaults: dict[str, object] = {
        "source": "vallenato-hoy",
        "title": "Un festival vallenato bate récord de asistencia",
        "url": "https://vallenatohoy.example.com/noticias/record-asistencia",
        "summary": "Miles de personas asistieron a la clausura del festival.",
        "hash": "abc123",
    }
    defaults.update(overrides)
    return NewsCandidate(**defaults)


def test_create_news_candidate_assigns_defaults() -> None:
    candidate = _build()

    assert candidate.id
    assert candidate.confidence == 1.0
    assert candidate.metadata == {}
    assert candidate.image_url is None
    assert candidate.published_at is None
    assert isinstance(candidate.discovered_at, datetime)


def test_create_news_candidate_accepts_explicit_values() -> None:
    discovered_at = datetime(2026, 7, 1, tzinfo=UTC)

    candidate = _build(
        id="candidate-1",
        image_url="https://vallenatohoy.example.com/img/record.jpg",
        published_at=datetime(2026, 6, 30, tzinfo=UTC),
        discovered_at=discovered_at,
        metadata={"category": "Festival"},
        confidence=0.8,
    )

    assert candidate.id == "candidate-1"
    assert candidate.discovered_at == discovered_at
    assert candidate.metadata == {"category": "Festival"}
    assert candidate.confidence == 0.8


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_create_news_candidate_rejects_out_of_range_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        _build(confidence=confidence)


@pytest.mark.parametrize("field_name", ["source", "title", "url", "hash"])
def test_create_news_candidate_rejects_empty_required_fields(field_name: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        _build(**{field_name: ""})


def test_news_candidate_is_immutable() -> None:
    candidate = _build()

    with pytest.raises(AttributeError):
        candidate.title = "Otro título"  # type: ignore[misc]
