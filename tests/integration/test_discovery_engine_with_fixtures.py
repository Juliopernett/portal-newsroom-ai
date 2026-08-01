"""Integration test: DiscoveryEngine running over real fixture-backed sources."""

from __future__ import annotations

from pathlib import Path

from core.entities.source import Source
from core.events.news_found import NewsFound
from core.services.discovery_engine import DiscoveryEngine
from tests.fakes.fake_content_source import FakeContentSource


def _adapter(fixtures_dir: Path, filename: str, priority: int) -> FakeContentSource:
    source = Source(name=filename, type="fixture", url=f"file://{filename}", priority=priority)
    return FakeContentSource(source=source, fixture_path=fixtures_dir / filename)


def test_discovery_engine_deduplicates_and_orders_real_fixtures(fixtures_dir: Path) -> None:
    silvestre = _adapter(fixtures_dir, "silvestre.json", priority=5)
    churo = _adapter(fixtures_dir, "churo.json", priority=3)
    festival = _adapter(fixtures_dir, "festival.json", priority=10)

    result = DiscoveryEngine().run([silvestre, churo, festival])

    assert isinstance(result, NewsFound)
    # 2 + 2 + 4 raw entries, minus 1 intra-source duplicate in festival.json.
    assert len(result.candidates) == 7
    # The highest-priority source (festival) should lead the ordered result.
    assert result.candidates[0].source == festival.source.id


def test_discovery_engine_skips_a_disabled_fixture_source(fixtures_dir: Path) -> None:
    churo = _adapter(fixtures_dir, "churo.json", priority=1)
    disabled_source = Source(
        name="silvestre.json", type="fixture", url="file://silvestre.json", enabled=False
    )
    silvestre_disabled = FakeContentSource(
        source=disabled_source, fixture_path=fixtures_dir / "silvestre.json"
    )

    result = DiscoveryEngine().run([churo, silvestre_disabled])

    assert len(result.candidates) == 2
    assert all(candidate.source == churo.source.id for candidate in result.candidates)
