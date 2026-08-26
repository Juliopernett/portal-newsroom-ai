"""Integration tests: /discovery — Radar Editorial listing and review actions.

`NewsCandidate` rows are never created through the API (only
`core.services.radar_service.descubrir` creates them) — every test here
seeds candidates directly through `SqlAlchemyNewsCandidateRepository`
against the same throwaway SQLite engine `client` already uses.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate
from database.repositories.news_candidate_repository import SqlAlchemyNewsCandidateRepository


def _candidato(**overrides: object) -> NewsCandidate:
    defaults: dict[str, object] = {
        "source": "fuente-1",
        "title": "Peter Manjarres anuncia nuevo disco",
        "url": "https://example.com/noticia",
        "summary": "Resumen de la noticia",
        "hash": "hash-1",
    }
    defaults.update(overrides)
    return NewsCandidate(**defaults)


def _seed(engine: Engine, candidato: NewsCandidate) -> None:
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    SqlAlchemyNewsCandidateRepository(session).save(candidato)
    session.commit()
    session.close()


def test_list_candidatos_returns_empty_list_when_none_exist(client: TestClient) -> None:
    response = client.get("/discovery")

    assert response.status_code == 200
    assert response.json() == []


def test_list_candidatos_returns_seeded_candidates(
    client: TestClient, _test_engine: Engine
) -> None:
    _seed(_test_engine, _candidato(hash="hash-1", title="Noticia uno"))
    _seed(_test_engine, _candidato(hash="hash-2", title="Noticia dos"))

    response = client.get("/discovery")

    assert response.status_code == 200
    titulos = {c["title"] for c in response.json()}
    assert titulos == {"Noticia uno", "Noticia dos"}


def test_list_candidatos_filters_by_estado(client: TestClient, _test_engine: Engine) -> None:
    _seed(_test_engine, _candidato(hash="hash-nuevo", estado=EstadoNewsCandidate.NUEVO))
    _seed(_test_engine, _candidato(hash="hash-guardado", estado=EstadoNewsCandidate.GUARDADO))

    response = client.get("/discovery", params={"estado": "guardado"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["estado"] == "guardado"


def test_list_candidatos_searches_by_q(client: TestClient, _test_engine: Engine) -> None:
    _seed(_test_engine, _candidato(hash="hash-a", title="Silvestre Dangond en concierto"))
    _seed(_test_engine, _candidato(hash="hash-b", title="Karen Lizarazo lanza sencillo"))

    response = client.get("/discovery", params={"q": "silvestre"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "Silvestre" in body[0]["title"]


def test_guardar_marks_the_candidate_guardado(client: TestClient, _test_engine: Engine) -> None:
    candidato = _candidato()
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/guardar")

    assert response.status_code == 200
    assert response.json()["estado"] == "guardado"


def test_descartar_marks_the_candidate_descartado(client: TestClient, _test_engine: Engine) -> None:
    candidato = _candidato()
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/descartar")

    assert response.status_code == 200
    assert response.json()["estado"] == "descartado"


def test_descartar_does_not_physically_delete_the_row(
    client: TestClient, _test_engine: Engine
) -> None:
    candidato = _candidato()
    _seed(_test_engine, candidato)

    client.post(f"/discovery/{candidato.id}/descartar")
    response = client.get("/discovery")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["estado"] == "descartado"


def test_crear_noticia_marks_the_candidate_procesado(
    client: TestClient, _test_engine: Engine
) -> None:
    candidato = _candidato()
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/crear-noticia")

    assert response.status_code == 200
    assert response.json()["estado"] == "procesado"


def test_action_on_an_already_procesado_candidate_returns_422(
    client: TestClient, _test_engine: Engine
) -> None:
    candidato = _candidato(estado=EstadoNewsCandidate.PROCESADO)
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/guardar")

    assert response.status_code == 422


def test_action_on_a_missing_id_returns_404(client: TestClient) -> None:
    response = client.post("/discovery/no-existe/guardar")

    assert response.status_code == 404


def test_list_candidatos_handles_a_candidate_without_summary_or_published_at(
    client: TestClient, _test_engine: Engine
) -> None:
    _seed(_test_engine, _candidato(summary="", published_at=None))

    response = client.get("/discovery")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["summary"] == ""
    assert body[0]["published_at"] is None


def test_list_candidatos_orders_nuevos_first_then_most_recent(
    client: TestClient, _test_engine: Engine
) -> None:
    guardado_reciente = _candidato(
        hash="hash-guardado",
        estado=EstadoNewsCandidate.GUARDADO,
        discovered_at=datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
    )
    nuevo_viejo = _candidato(
        hash="hash-nuevo",
        title="Nuevo",
        discovered_at=datetime(2026, 8, 26, 8, 0, tzinfo=UTC),
    )
    _seed(_test_engine, guardado_reciente)
    _seed(_test_engine, nuevo_viejo)

    response = client.get("/discovery")

    body = response.json()
    assert body[0]["title"] == "Nuevo"
