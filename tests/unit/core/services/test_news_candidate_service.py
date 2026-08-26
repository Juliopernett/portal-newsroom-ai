"""Unit tests for news_candidate_service — no network, no database."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate
from core.services.news_candidate_service import (
    crear_noticia,
    descartar,
    guardar,
    ordenar_para_revision,
)


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


def test_guardar_transitions_to_guardado() -> None:
    candidato = _candidato()

    resultado = guardar(candidato)

    assert resultado.estado == EstadoNewsCandidate.GUARDADO


def test_guardar_does_not_mutate_the_original() -> None:
    candidato = _candidato()

    guardar(candidato)

    assert candidato.estado == EstadoNewsCandidate.NUEVO


def test_guardar_allows_changing_your_mind_after_descartado() -> None:
    candidato = _candidato(estado=EstadoNewsCandidate.DESCARTADO)

    resultado = guardar(candidato)

    assert resultado.estado == EstadoNewsCandidate.GUARDADO


def test_guardar_rejects_a_procesado_candidato() -> None:
    candidato = _candidato(estado=EstadoNewsCandidate.PROCESADO)

    with pytest.raises(ValueError, match="terminal"):
        guardar(candidato)


def test_descartar_transitions_to_descartado() -> None:
    candidato = _candidato()

    resultado = descartar(candidato)

    assert resultado.estado == EstadoNewsCandidate.DESCARTADO


def test_descartar_rejects_a_procesado_candidato() -> None:
    candidato = _candidato(estado=EstadoNewsCandidate.PROCESADO)

    with pytest.raises(ValueError, match="terminal"):
        descartar(candidato)


def test_crear_noticia_transitions_to_procesado() -> None:
    candidato = _candidato()

    resultado = crear_noticia(candidato)

    assert resultado.estado == EstadoNewsCandidate.PROCESADO


def test_crear_noticia_rejects_a_candidato_already_procesado() -> None:
    candidato = _candidato(estado=EstadoNewsCandidate.PROCESADO)

    with pytest.raises(ValueError, match="terminal"):
        crear_noticia(candidato)


def test_crear_noticia_does_not_mutate_the_original() -> None:
    candidato = _candidato()

    crear_noticia(candidato)

    assert candidato.estado == EstadoNewsCandidate.NUEVO


def test_ordenar_para_revision_with_an_empty_list() -> None:
    assert ordenar_para_revision([]) == []


def test_ordenar_para_revision_puts_nuevos_first() -> None:
    guardado = _candidato(
        hash="a",
        estado=EstadoNewsCandidate.GUARDADO,
        discovered_at=datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
    )
    nuevo = _candidato(
        hash="b",
        estado=EstadoNewsCandidate.NUEVO,
        discovered_at=datetime(2026, 8, 26, 10, 0, tzinfo=UTC),
    )

    resultado = ordenar_para_revision([guardado, nuevo])

    assert resultado == [nuevo, guardado]


def test_ordenar_para_revision_sorts_by_most_recent_within_the_same_bucket() -> None:
    mas_viejo = _candidato(hash="a", discovered_at=datetime(2026, 8, 25, tzinfo=UTC))
    mas_nuevo = _candidato(hash="b", discovered_at=datetime(2026, 8, 26, tzinfo=UTC))

    resultado = ordenar_para_revision([mas_viejo, mas_nuevo])

    assert resultado == [mas_nuevo, mas_viejo]


def test_ordenar_para_revision_handles_a_candidato_without_published_at() -> None:
    candidato = _candidato(published_at=None)

    resultado = ordenar_para_revision([candidato])

    assert resultado == [candidato]


def test_ordenar_para_revision_handles_a_candidato_without_summary() -> None:
    candidato = _candidato(summary="")

    resultado = ordenar_para_revision([candidato])

    assert resultado == [candidato]
