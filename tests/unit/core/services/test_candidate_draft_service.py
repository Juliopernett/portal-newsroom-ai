"""Unit tests for candidate_draft_service — fake AI and CMS, no network."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from agents.ai.fake_provider import FakeAIProvider
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
from core.ports.portada_renderer import SolicitudPortada
from core.services.candidate_draft_service import (
    BorradorDesdeCandidatoError,
    PortadaParaBorrador,
    crear_borrador_desde_candidato,
    sincronizar_estado_wordpress,
)


class _FakeCMS:
    def __init__(self) -> None:
        self.contenido: dict[str, Any] | None = None
        self.llamadas_create = 0
        self.media_subida: list[tuple[str, bytes]] = []
        self.consultas = 0
        self.consulta = ConsultaPostCMS(
            estado=EstadoPostCMS.BORRADOR, url=None, fecha_publicacion=None
        )

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        self.llamadas_create += 1
        self.contenido = content
        return CMSDraftResult(post_id="77", url="https://www.portalvallenato.com/?p=77")

    def subir_media_con_url(
        self, contenido: bytes, nombre_archivo: str, content_type: str
    ) -> MediaSubidaCMS:
        self.media_subida.append((nombre_archivo, contenido))
        return MediaSubidaCMS(id="media-9", url="https://www.portalvallenato.com/portada.jpg")

    def consultar_estado_post(self, post_id: str) -> ConsultaPostCMS:
        self.consultas += 1
        return self.consulta

    def listar_categorias(self) -> list[CategoriaCMS]:
        return [CategoriaCMS(id="3", nombre="Noticias")]

    def resolver_o_crear_etiqueta(self, nombre: str) -> str:
        return f"tag-{nombre}"


def _candidato(**overrides: object) -> NewsCandidate:
    extraido = ExtractedContent(
        title="Titular original",
        body="Cuerpo original de la nota.",
        source_url="https://elpilon.com.co/nota",
        site_name="El Pilón",
    )
    defaults: dict[str, object] = {
        "source": "fuente",
        "title": "Titular",
        "url": "https://news.google.com/x",
        "summary": "r",
        "hash": "h",
        "extracted_content": extraido,
    }
    defaults.update(overrides)
    return NewsCandidate(**defaults)


_RESPUESTA = json.dumps(
    {
        "titulo": "Titular reescrito",
        "entradilla": "Entradilla",
        "contenido": "Cuerpo reescrito",
        "categoria": "Noticias",
        "etiquetas": ["Vallenato", " "],
        "slug": "titular-reescrito",
        "meta_titulo": "Meta",
        "meta_descripcion": "Desc",
        "frase_clave": "vallenato",
        "texto_redes": "Gancho para redes\n#Vallenato #Festival",
    }
)


def test_creates_a_draft_and_marks_the_candidate_procesado() -> None:
    cms = _FakeCMS()

    resultado = crear_borrador_desde_candidato(
        _candidato(), FakeAIProvider(respuesta_json=_RESPUESTA), cms
    )

    assert resultado.estado == EstadoNewsCandidate.PROCESADO
    assert resultado.wp_post_id == "77"
    assert resultado.wp_url == "https://www.portalvallenato.com/?p=77"
    assert cms.contenido is not None
    assert cms.contenido["title"] == "Titular reescrito"
    assert cms.contenido["categories"] == ["3"]
    assert cms.contenido["tags"] == ["tag-Vallenato"]
    assert cms.contenido["meta"]["_yoast_wpseo_focuskw"] == "vallenato"


def test_draft_credits_the_original_source() -> None:
    cms = _FakeCMS()

    crear_borrador_desde_candidato(_candidato(), FakeAIProvider(respuesta_json=_RESPUESTA), cms)

    assert cms.contenido is not None
    assert 'href="https://elpilon.com.co/nota"' in cms.contenido["content"]
    assert "El Pilón" in cms.contenido["content"]


def test_ai_failure_creates_no_draft() -> None:
    cms = _FakeCMS()

    with pytest.raises(BorradorDesdeCandidatoError):
        crear_borrador_desde_candidato(
            _candidato(), FakeAIProvider(error=AIProviderError("sin saldo")), cms
        )

    assert cms.llamadas_create == 0


def test_requires_extracted_content() -> None:
    with pytest.raises(ValueError, match="Preparar noticia"):
        crear_borrador_desde_candidato(
            _candidato(extracted_content=None), FakeAIProvider(), _FakeCMS()
        )


class _FakeRenderer:
    def __init__(self) -> None:
        self.solicitud: SolicitudPortada | None = None

    def renderizar(self, solicitud: SolicitudPortada, *, formato: str = "png") -> bytes:
        self.solicitud = solicitud
        return b"portada-jpeg"


def test_with_a_portada_it_uploads_the_cover_as_featured_image() -> None:
    cms = _FakeCMS()
    renderer = _FakeRenderer()

    resultado = crear_borrador_desde_candidato(
        _candidato(),
        FakeAIProvider(respuesta_json=_RESPUESTA),
        cms,
        portada=PortadaParaBorrador(imagen_base=b"foto"),
        portada_renderer=renderer,
    )

    assert cms.contenido is not None
    assert cms.contenido["featured_media"] == "media-9"
    assert resultado.portada_url == "https://www.portalvallenato.com/portada.jpg"
    assert cms.media_subida == [("portada-titular-reescrito.jpg", b"portada-jpeg")]
    # No headline given: the cover uses the one the AI wrote.
    assert renderer.solicitud is not None
    assert renderer.solicitud.titular == "Titular reescrito"


def test_portada_titular_overrides_the_ai_headline() -> None:
    renderer = _FakeRenderer()

    crear_borrador_desde_candidato(
        _candidato(),
        FakeAIProvider(respuesta_json=_RESPUESTA),
        _FakeCMS(),
        portada=PortadaParaBorrador(imagen_base=b"foto", titular="Mi titular corto"),
        portada_renderer=renderer,
    )

    assert renderer.solicitud is not None
    assert renderer.solicitud.titular == "Mi titular corto"


def test_without_a_portada_no_image_is_attached() -> None:
    cms = _FakeCMS()

    resultado = crear_borrador_desde_candidato(
        _candidato(), FakeAIProvider(respuesta_json=_RESPUESTA), cms
    )

    assert cms.contenido is not None
    assert "featured_media" not in cms.contenido
    assert resultado.portada_url is None


class _FakeStorage:
    def __init__(self) -> None:
        self.guardado: dict[str, bytes] = {}

    def guardar(self, key: str, contenido: bytes) -> None:
        self.guardado[key] = contenido

    def leer(self, key: str) -> bytes:
        return self.guardado[key]

    def eliminar(self, key: str) -> None:
        self.guardado.pop(key, None)


def test_keeps_the_jpeg_in_the_app_storage_and_stores_the_social_text() -> None:
    storage = _FakeStorage()
    candidato = _candidato()

    resultado = crear_borrador_desde_candidato(
        candidato,
        FakeAIProvider(respuesta_json=_RESPUESTA),
        _FakeCMS(),
        portada=PortadaParaBorrador(imagen_base=b"foto"),
        portada_renderer=_FakeRenderer(),
        media_storage=storage,
    )

    assert resultado.portada_storage_key == f"portadas/{candidato.id}.jpg"
    assert storage.guardado[resultado.portada_storage_key] == b"portada-jpeg"
    assert resultado.tiene_portada_guardada is True
    assert resultado.texto_redes == "Gancho para redes\n#Vallenato #Festival"
    assert resultado.wp_estado == "borrador"


def _procesado(**overrides: object) -> NewsCandidate:
    defaults: dict[str, object] = {
        "estado": EstadoNewsCandidate.PROCESADO,
        "wp_post_id": "77",
        "wp_estado": "borrador",
    }
    defaults.update(overrides)
    return _candidato(**defaults)


def test_sync_marks_a_published_post_with_its_real_url_and_date() -> None:
    cms = _FakeCMS()
    fecha = datetime(2026, 10, 29, tzinfo=UTC)
    cms.consulta = ConsultaPostCMS(
        estado=EstadoPostCMS.PUBLICADO,
        url="https://www.portalvallenato.com/nota/",
        fecha_publicacion=fecha,
    )

    resultado = sincronizar_estado_wordpress(_procesado(), cms)

    assert resultado.wp_estado == "publicado"
    assert resultado.wp_publicado_url == "https://www.portalvallenato.com/nota/"
    assert resultado.wp_fecha_publicacion == fecha


def test_sync_detects_a_trashed_post() -> None:
    cms = _FakeCMS()
    cms.consulta = ConsultaPostCMS(estado=EstadoPostCMS.ELIMINADO, url=None, fecha_publicacion=None)

    assert sincronizar_estado_wordpress(_procesado(), cms).wp_estado == "eliminado"


def test_sync_keeps_what_was_known_when_wordpress_cannot_be_checked() -> None:
    cms = _FakeCMS()
    cms.consulta = ConsultaPostCMS(estado=EstadoPostCMS.ERROR, url=None, fecha_publicacion=None)
    candidato = _procesado()

    assert sincronizar_estado_wordpress(candidato, cms) == candidato


def test_sync_never_asks_wordpress_again_once_published() -> None:
    cms = _FakeCMS()

    resultado = sincronizar_estado_wordpress(_procesado(wp_estado="publicado"), cms)

    assert resultado.wp_estado == "publicado"
    assert cms.consultas == 0


def test_a_portada_without_renderer_is_rejected() -> None:
    with pytest.raises(ValueError, match="portada_renderer"):
        crear_borrador_desde_candidato(
            _candidato(),
            FakeAIProvider(),
            _FakeCMS(),
            portada=PortadaParaBorrador(imagen_base=b"foto"),
        )


def test_rejects_an_already_procesado_candidate() -> None:
    with pytest.raises(ValueError):
        crear_borrador_desde_candidato(
            _candidato(estado=EstadoNewsCandidate.PROCESADO), FakeAIProvider(), _FakeCMS()
        )
