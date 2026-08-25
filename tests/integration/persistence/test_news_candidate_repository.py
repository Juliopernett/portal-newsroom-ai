"""Integration tests: SqlAlchemyNewsCandidateRepository against a real SQLite schema."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core.entities.news_candidate import NewsCandidate
from database.repositories.news_candidate_repository import SqlAlchemyNewsCandidateRepository


def _candidato(**overrides: object) -> NewsCandidate:
    defaults: dict[str, object] = {
        "source": "fuente-1",
        "title": "Peter Manjarres anuncia nuevo disco",
        "url": "https://example.com/peter-manjarres",
        "summary": "Resumen de la noticia.",
        "hash": "hash-unico-1",
        "published_at": datetime(2026, 8, 25, 10, 0, tzinfo=UTC),
        "metadata": {"guid": "guid-1"},
    }
    defaults.update(overrides)
    return NewsCandidate(**defaults)


def test_exists_is_false_before_saving(session: Session) -> None:
    repository = SqlAlchemyNewsCandidateRepository(session)

    assert repository.exists("no-existe") is False


def test_save_and_exists_round_trip(session: Session) -> None:
    repository = SqlAlchemyNewsCandidateRepository(session)
    candidato = _candidato()

    repository.save(candidato)
    session.commit()

    assert repository.exists("hash-unico-1") is True


def test_list_all_returns_every_persisted_candidate_with_fields_intact(session: Session) -> None:
    repository = SqlAlchemyNewsCandidateRepository(session)
    candidato = _candidato()

    repository.save(candidato)
    session.commit()

    resultado = repository.list_all()

    assert len(resultado) == 1
    recuperado = resultado[0]
    assert recuperado.title == candidato.title
    assert recuperado.url == candidato.url
    assert recuperado.summary == candidato.summary
    assert recuperado.hash == candidato.hash
    assert recuperado.metadata == {"guid": "guid-1"}
    assert recuperado.published_at == datetime(2026, 8, 25, 10, 0, tzinfo=UTC)


def test_list_all_returns_empty_dict_metadata_when_none_was_set(session: Session) -> None:
    repository = SqlAlchemyNewsCandidateRepository(session)
    repository.save(_candidato(hash="sin-metadata", metadata={}))
    session.commit()

    resultado = repository.list_all()

    assert resultado[0].metadata == {}


def test_save_twice_with_the_same_id_does_not_create_a_duplicate_row(session: Session) -> None:
    repository = SqlAlchemyNewsCandidateRepository(session)
    candidato = _candidato()

    repository.save(candidato)
    session.commit()
    repository.save(candidato)
    session.commit()

    assert len(repository.list_all()) == 1
