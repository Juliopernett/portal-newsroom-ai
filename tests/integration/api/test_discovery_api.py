"""Integration tests: /discovery — Radar Editorial listing and review actions.

`NewsCandidate` rows are never created through the API (only
`core.services.radar_service.descubrir` creates them) — every test here
seeds candidates directly through `SqlAlchemyNewsCandidateRepository`
against the same throwaway SQLite engine `client` already uses.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from agents.ai.fake_provider import FakeAIProvider
from agents.extractor.fake_content_extractor import FakeContentExtractor
from agents.radar.fake_source_resolver import FakeSourceResolver
from app.api.dependencies import (
    get_ai_provider,
    get_cms_publisher,
    get_content_extractor,
    get_media_storage,
    get_source_resolver,
)
from app.api.main import app
from core.entities.extracted_content import ExtractedContent
from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate
from core.ports.ai_provider import AIProviderError
from core.ports.cms_publisher import (
    CategoriaCMS,
    CMSDraftResult,
    ConsultaPostCMS,
    EstadoPostCMS,
    MediaSubidaCMS,
)
from core.ports.content_extractor import ContentExtractorError
from core.ports.source_resolver import ResolvedSource
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


class _FakeCMS:
    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        return CMSDraftResult(post_id="42", url="https://www.portalvallenato.com/?p=42")

    def consultar_estado_post(self, post_id: str) -> ConsultaPostCMS:
        return ConsultaPostCMS(
            estado=EstadoPostCMS.PUBLICADO,
            url="https://www.portalvallenato.com/la-nota/",
            fecha_publicacion=datetime(2026, 10, 29, tzinfo=UTC),
        )

    def listar_categorias(self) -> list[CategoriaCMS]:
        return []

    def resolver_o_crear_etiqueta(self, nombre: str) -> str:
        return "1"

    def subir_media_con_url(
        self, contenido: bytes, nombre_archivo: str, content_type: str
    ) -> MediaSubidaCMS:
        assert contenido[:2] == b"\xff\xd8"  # a real JPEG, rendered by the real renderer
        return MediaSubidaCMS(id="7", url="https://www.portalvallenato.com/portada.jpg")


def _con_cms_falso() -> None:
    app.dependency_overrides[get_cms_publisher] = lambda: _FakeCMS()


def _extraido() -> ExtractedContent:
    return ExtractedContent(title="T", body="Cuerpo", source_url="https://medio.com/nota")


def test_crear_noticia_creates_a_wordpress_draft_and_marks_procesado(
    client: TestClient, _test_engine: Engine
) -> None:
    _con_cms_falso()
    candidato = _candidato(extracted_content=_extraido())
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/crear-noticia")

    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "procesado"
    assert body["wp_post_id"] == "42"
    assert body["wp_url"] == "https://www.portalvallenato.com/?p=42"


def test_crear_noticia_with_a_photo_renders_and_stores_the_cover(
    client: TestClient, _test_engine: Engine
) -> None:
    _con_cms_falso()
    candidato = _candidato(extracted_content=_extraido())
    _seed(_test_engine, candidato)
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), (200, 120, 40)).save(buffer, "JPEG")

    response = client.post(
        f"/discovery/{candidato.id}/crear-noticia",
        files={"imagen_base": ("foto.jpg", buffer.getvalue(), "image/jpeg")},
        data={"variante": "lo_ultimo", "titular_portada": "Titular corto"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "procesado"
    assert body["portada_url"] == "https://www.portalvallenato.com/portada.jpg"


class _MemoriaStorage:
    def __init__(self) -> None:
        self.archivos: dict[str, bytes] = {}

    def guardar(self, key: str, contenido: bytes) -> None:
        self.archivos[key] = contenido

    def leer(self, key: str) -> bytes:
        return self.archivos[key]

    def eliminar(self, key: str) -> None:
        self.archivos.pop(key, None)


def test_the_stored_jpeg_can_be_downloaded(client: TestClient, _test_engine: Engine) -> None:
    _con_cms_falso()
    app.dependency_overrides[get_media_storage] = lambda: storage
    storage = _MemoriaStorage()
    candidato = _candidato(extracted_content=_extraido())
    _seed(_test_engine, candidato)
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), (200, 120, 40)).save(buffer, "JPEG")
    client.post(
        f"/discovery/{candidato.id}/crear-noticia",
        files={"imagen_base": ("foto.jpg", buffer.getvalue(), "image/jpeg")},
    )

    response = client.get(f"/discovery/{candidato.id}/portada.jpg")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content[:2] == b"\xff\xd8"
    assert client.get("/discovery").json()[0]["tiene_portada_guardada"] is True


def test_downloading_a_cover_that_was_never_stored_returns_404(
    client: TestClient, _test_engine: Engine
) -> None:
    candidato = _candidato(portada_url="https://wp/portada.webp")
    _seed(_test_engine, candidato)

    assert client.get(f"/discovery/{candidato.id}/portada.jpg").status_code == 404


def test_sincronizar_wordpress_refreshes_processed_candidates(
    client: TestClient, _test_engine: Engine
) -> None:
    _con_cms_falso()
    procesado = _candidato(
        hash="h-p",
        estado=EstadoNewsCandidate.PROCESADO,
        wp_post_id="42",
        wp_estado="borrador",
    )
    _seed(_test_engine, procesado)
    _seed(_test_engine, _candidato(hash="h-n"))

    response = client.post("/discovery/sincronizar-wordpress")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1  # only candidates with a WordPress draft
    assert body[0]["wp_estado"] == "publicado"
    assert body[0]["wp_publicado_url"] == "https://www.portalvallenato.com/la-nota/"
    persistido = next(c for c in client.get("/discovery").json() if c["id"] == procesado.id)
    assert persistido["wp_estado"] == "publicado"


def test_crear_noticia_without_extracted_content_returns_422(
    client: TestClient, _test_engine: Engine
) -> None:
    _con_cms_falso()
    candidato = _candidato()
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/crear-noticia")

    assert response.status_code == 422
    assert client.get("/discovery").json()[0]["estado"] == "nuevo"


def test_crear_noticia_returns_502_and_creates_nothing_when_the_ai_fails(
    client: TestClient, _test_engine: Engine
) -> None:
    _con_cms_falso()
    app.dependency_overrides[get_ai_provider] = lambda: FakeAIProvider(
        error=AIProviderError("sin saldo")
    )
    candidato = _candidato(extracted_content=_extraido())
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/crear-noticia")

    assert response.status_code == 502
    persistido = client.get("/discovery").json()[0]
    assert persistido["estado"] == "nuevo"
    assert persistido["wp_post_id"] is None


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


def test_preparar_resolves_and_extracts_on_success(
    client: TestClient, _test_engine: Engine
) -> None:
    candidato = _candidato()
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/preparar")

    assert response.status_code == 200
    body = response.json()
    assert body["estado_resolucion"] == "resuelta"
    assert body["url_fuente_original"] is not None
    assert body["extracted_content"] is not None
    assert body["extracted_content"]["title"] == "[DEMO] Titular extraído"
    # No editorial-state side effect — "preparar" never marks procesado.
    assert body["estado"] == "nuevo"


def test_preparar_does_not_500_when_resolution_fails(
    client: TestClient, _test_engine: Engine
) -> None:
    candidato = _candidato()
    _seed(_test_engine, candidato)
    app.dependency_overrides[get_source_resolver] = lambda: FakeSourceResolver(
        resultado=ResolvedSource(success=False, resolved_url=None, error="timeout")
    )

    response = client.post(f"/discovery/{candidato.id}/preparar")

    assert response.status_code == 200
    body = response.json()
    assert body["estado_resolucion"] == "fallida"
    assert body["url_fuente_original"] is None
    assert body["extracted_content"] is None


def test_preparar_does_not_500_when_extraction_fails(
    client: TestClient, _test_engine: Engine
) -> None:
    candidato = _candidato()
    _seed(_test_engine, candidato)
    app.dependency_overrides[get_content_extractor] = lambda: FakeContentExtractor(
        error=ContentExtractorError("sin contenido reconocible")
    )

    response = client.post(f"/discovery/{candidato.id}/preparar")

    assert response.status_code == 200
    body = response.json()
    assert body["estado_resolucion"] == "resuelta"
    assert body["extracted_content"] is None


def test_preparar_on_a_missing_id_returns_404(client: TestClient) -> None:
    response = client.post("/discovery/no-existe/preparar")

    assert response.status_code == 404


def test_preparar_does_not_lose_a_descartado_candidate(
    client: TestClient, _test_engine: Engine
) -> None:
    """Preparing is independent of estado — even a descartado candidate can be prepared."""
    candidato = _candidato(estado=EstadoNewsCandidate.DESCARTADO)
    _seed(_test_engine, candidato)

    response = client.post(f"/discovery/{candidato.id}/preparar")

    assert response.status_code == 200
    assert response.json()["estado"] == "descartado"
    assert response.json()["estado_resolucion"] == "resuelta"


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

    response = client.get("/discovery", params={"dias": 0})

    body = response.json()
    assert body[0]["title"] == "Nuevo"


def test_list_hides_old_unreviewed_candidates_but_never_reviewed_ones(
    client: TestClient, _test_engine: Engine
) -> None:
    viejo = datetime(2026, 1, 1, tzinfo=UTC)
    _seed(_test_engine, _candidato(hash="h-nuevo-viejo", title="Nuevo viejo", discovered_at=viejo))
    _seed(
        _test_engine,
        _candidato(
            hash="h-procesado-viejo",
            title="Procesado viejo",
            estado=EstadoNewsCandidate.PROCESADO,
            discovered_at=viejo,
        ),
    )
    _seed(_test_engine, _candidato(hash="h-nuevo-hoy", title="Nuevo hoy"))

    por_defecto = {c["title"] for c in client.get("/discovery").json()}
    todo = {c["title"] for c in client.get("/discovery", params={"dias": 0}).json()}

    assert por_defecto == {"Procesado viejo", "Nuevo hoy"}
    assert todo == {"Nuevo viejo", "Procesado viejo", "Nuevo hoy"}
