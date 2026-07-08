"""Unit tests for DiscoveryEngine, using in-memory ContentSource doubles."""

from __future__ import annotations

from datetime import UTC, datetime

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source
from core.events.news_found import NewsFound
from core.services.discovery_engine import DiscoveryEngine


class _StubContentSource:
    """Minimal in-memory ContentSource double for engine-only tests."""

    def __init__(self, source: Source, candidates: list[NewsCandidate]) -> None:
        self._source = source
        self._candidates = candidates

    @property
    def source(self) -> Source:
        return self._source

    def fetch_candidates(self) -> list[NewsCandidate]:
        return self._candidates


def _candidate(**overrides: object) -> NewsCandidate:
    defaults: dict[str, object] = {
        "source": "source-a",
        "title": "Título de ejemplo",
        "url": "https://example.com/a",
        "summary": "Resumen de ejemplo.",
        "hash": "hash-a",
        "confidence": 1.0,
    }
    defaults.update(overrides)
    return NewsCandidate(**defaults)


def test_run_returns_news_found_event() -> None:
    source = Source(name="Source A", type="rss", url="https://example.com/feed")
    stub = _StubContentSource(source, [_candidate(source=source.id, hash="h1")])

    result = DiscoveryEngine().run([stub])

    assert isinstance(result, NewsFound)
    assert len(result.candidates) == 1


def test_run_with_no_sources_returns_an_empty_event() -> None:
    result = DiscoveryEngine().run([])

    assert result.candidates == ()


def test_run_skips_disabled_sources() -> None:
    source = Source(name="Source A", type="rss", url="https://example.com/feed", enabled=False)
    stub = _StubContentSource(source, [_candidate(source=source.id, hash="h1")])

    result = DiscoveryEngine().run([stub])

    assert result.candidates == ()


def test_run_deduplicates_by_hash_keeping_the_first_occurrence() -> None:
    source = Source(name="Source A", type="rss", url="https://example.com/feed")
    first = _candidate(source=source.id, hash="dup", title="Primera versión")
    second = _candidate(source=source.id, hash="dup", title="Segunda versión")
    stub = _StubContentSource(source, [first, second])

    result = DiscoveryEngine().run([stub])

    assert len(result.candidates) == 1
    assert result.candidates[0].title == "Primera versión"


def test_run_deduplicates_across_sources() -> None:
    source_a = Source(name="Source A", type="rss", url="https://a.example.com/feed")
    source_b = Source(name="Source B", type="rss", url="https://b.example.com/feed")
    shared_hash = "shared"
    stub_a = _StubContentSource(source_a, [_candidate(source=source_a.id, hash=shared_hash)])
    stub_b = _StubContentSource(source_b, [_candidate(source=source_b.id, hash=shared_hash)])

    result = DiscoveryEngine().run([stub_a, stub_b])

    assert len(result.candidates) == 1


def test_run_orders_by_source_priority_descending() -> None:
    low = Source(name="Low", type="rss", url="https://low.example.com/feed", priority=1)
    high = Source(name="High", type="rss", url="https://high.example.com/feed", priority=10)
    stub_low = _StubContentSource(
        low, [_candidate(source=low.id, hash="low", title="Baja prioridad")]
    )
    stub_high = _StubContentSource(
        high, [_candidate(source=high.id, hash="high", title="Alta prioridad")]
    )

    result = DiscoveryEngine().run([stub_low, stub_high])

    assert [c.title for c in result.candidates] == ["Alta prioridad", "Baja prioridad"]


def test_run_orders_by_confidence_within_the_same_source_priority() -> None:
    source = Source(name="Source A", type="rss", url="https://example.com/feed", priority=5)
    low_confidence = _candidate(
        source=source.id, hash="low", title="Menos confiable", confidence=0.4
    )
    high_confidence = _candidate(
        source=source.id, hash="high", title="Más confiable", confidence=0.9
    )
    stub = _StubContentSource(source, [low_confidence, high_confidence])

    result = DiscoveryEngine().run([stub])

    assert [c.title for c in result.candidates] == ["Más confiable", "Menos confiable"]


def test_run_uses_injected_clock_for_event_timestamp() -> None:
    fixed_time = datetime(2026, 7, 1, tzinfo=UTC)
    engine = DiscoveryEngine(clock=lambda: fixed_time)

    result = engine.run([])

    assert result.occurred_at == fixed_time
