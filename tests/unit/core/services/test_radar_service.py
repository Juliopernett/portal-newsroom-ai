"""Unit tests for radar_service.descubrir — in-memory stub source and repository."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.news_candidate import NewsCandidate
from core.entities.source import Source
from core.ports.content_source import ContentSourceError
from core.services.discovery_engine import DiscoveryEngine
from core.services.radar_service import ResultadoDescubrimiento, descubrir


def _candidato(**overrides: object) -> NewsCandidate:
    defaults: dict[str, object] = {
        "source": "fuente-1",
        "title": "Titulo",
        "url": "https://example.com/noticia",
        "summary": "Resumen",
        "hash": "hash-1",
    }
    defaults.update(overrides)
    return NewsCandidate(**defaults)


class _StubContentSource:
    """In-memory ContentSource — returns a fixed list or raises."""

    def __init__(
        self,
        source: Source,
        candidates: list[NewsCandidate] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._source = source
        self._candidates = candidates or []
        self._error = error

    @property
    def source(self) -> Source:
        return self._source

    def fetch_candidates(self) -> list[NewsCandidate]:
        if self._error is not None:
            raise self._error
        return self._candidates


class _FakeNewsCandidateRepository:
    """In-memory NewsCandidateRepository — no database."""

    def __init__(self) -> None:
        self._by_hash: dict[str, NewsCandidate] = {}

    def save(self, entity: NewsCandidate) -> None:
        self._by_hash[entity.hash] = entity

    def exists(self, reference: str) -> bool:
        return reference in self._by_hash

    def list_all(self) -> list[NewsCandidate]:
        return list(self._by_hash.values())


def _source(**overrides: object) -> Source:
    defaults: dict[str, object] = {"name": "Fuente de prueba", "type": "rss", "url": "https://example.com"}
    defaults.update(overrides)
    return Source(**defaults)


def test_descubrir_persists_every_new_candidate() -> None:
    fuente = _source()
    candidatos = [_candidato(hash="hash-1"), _candidato(hash="hash-2")]
    source_adapter = _StubContentSource(fuente, candidatos)
    repository = _FakeNewsCandidateRepository()

    resultado = descubrir(source_adapter, repository)

    assert resultado.consultados == 2
    assert resultado.nuevos == 2
    assert resultado.duplicados == 0
    assert resultado.errores == 0
    assert len(repository.list_all()) == 2


def test_descubrir_twice_is_idempotent() -> None:
    fuente = _source()
    candidatos = [_candidato(hash="hash-1"), _candidato(hash="hash-2")]
    repository = _FakeNewsCandidateRepository()

    descubrir(_StubContentSource(fuente, candidatos), repository)
    segunda = descubrir(_StubContentSource(fuente, candidatos), repository)

    assert segunda.nuevos == 0
    assert segunda.duplicados == 2
    assert len(repository.list_all()) == 2  # no se duplicó nada


def test_descubrir_counts_a_pre_existing_candidate_as_duplicate() -> None:
    fuente = _source()
    repository = _FakeNewsCandidateRepository()
    repository.save(_candidato(hash="ya-existia"))

    resultado = descubrir(
        _StubContentSource(fuente, [_candidato(hash="ya-existia"), _candidato(hash="nueva")]),
        repository,
    )

    assert resultado.nuevos == 1
    assert resultado.duplicados == 1


def test_descubrir_reports_errores_on_content_source_error_without_raising() -> None:
    fuente = _source()
    repository = _FakeNewsCandidateRepository()
    source_adapter = _StubContentSource(fuente, error=ContentSourceError("fuente no disponible"))

    resultado = descubrir(source_adapter, repository)

    assert resultado.errores == 1
    assert resultado.consultados == 0
    assert resultado.nuevos == 0
    assert resultado.duplicados == 0
    assert repository.list_all() == []


def test_descubrir_with_no_candidates_reports_all_zero() -> None:
    fuente = _source()
    repository = _FakeNewsCandidateRepository()

    resultado = descubrir(_StubContentSource(fuente, []), repository)

    assert resultado == ResultadoDescubrimiento(
        fuente=fuente.name, consultados=0, nuevos=0, duplicados=0, errores=0
    )


def test_descubrir_reports_the_source_name() -> None:
    fuente = _source(name="Google Noticias - vallenato")
    repository = _FakeNewsCandidateRepository()

    resultado = descubrir(_StubContentSource(fuente, []), repository)

    assert resultado.fuente == "Google Noticias - vallenato"


def test_descubrir_does_not_propagate_a_non_content_source_error() -> None:
    """Only ContentSourceError is treated as a source-level failure — anything
    else (a real bug) should surface loudly, not be silently swallowed."""
    fuente = _source()
    repository = _FakeNewsCandidateRepository()
    source_adapter = _StubContentSource(fuente, error=ValueError("bug real"))

    with pytest.raises(ValueError, match="bug real"):
        descubrir(source_adapter, repository)


def test_descubrir_uses_a_fixed_clock_when_engine_is_injected() -> None:
    fuente = _source()
    fecha_fija = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)
    repository = _FakeNewsCandidateRepository()
    engine = DiscoveryEngine(clock=lambda: fecha_fija)

    resultado = descubrir(_StubContentSource(fuente, [_candidato()]), repository, engine=engine)

    assert resultado.nuevos == 1
