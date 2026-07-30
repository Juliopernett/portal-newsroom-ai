"""Integration tests: FakeContentSource reading real fixture files."""

from __future__ import annotations

from pathlib import Path

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source
from tests.fakes.fake_content_source import FakeContentSource


def _make_adapter(fixtures_dir: Path, filename: str, **overrides: object) -> FakeContentSource:
    defaults: dict[str, object] = {"name": filename, "type": "fixture", "url": f"file://{filename}"}
    defaults.update(overrides)
    source = Source(**defaults)
    return FakeContentSource(source=source, fixture_path=fixtures_dir / filename)


def test_fetch_candidates_reads_all_entries_from_a_fixture(fixtures_dir: Path) -> None:
    adapter = _make_adapter(fixtures_dir, "silvestre.json")

    candidates = adapter.fetch_candidates()

    assert len(candidates) == 2
    assert all(isinstance(candidate, NewsCandidate) for candidate in candidates)
    assert all(candidate.source == adapter.source.id for candidate in candidates)


def test_fetch_candidates_maps_fixture_fields(fixtures_dir: Path) -> None:
    adapter = _make_adapter(fixtures_dir, "churo.json")

    candidates = adapter.fetch_candidates()
    first = candidates[0]

    assert first.title == (
        "El 'churo' del acordeón: la ornamentación que distingue a los grandes maestros"
    )
    assert first.url.startswith("https://elpiloncultural.example.com/")
    assert first.image_url is not None
    assert first.published_at is not None
    assert first.metadata == {"category": "Técnica Vallenata"}
    assert 0.0 <= first.confidence <= 1.0


def test_fetch_candidates_computes_a_stable_hash_per_url(fixtures_dir: Path) -> None:
    adapter = _make_adapter(fixtures_dir, "festival.json")

    candidates = adapter.fetch_candidates()
    hashes = [candidate.hash for candidate in candidates]

    # festival.json intentionally repeats one URL to exercise deduplication.
    assert len(hashes) == 4
    assert len(set(hashes)) == 3
