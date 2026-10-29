"""Unit tests for candidate_draft_service — fake AI and CMS, no network."""

from __future__ import annotations

import json
from typing import Any

import pytest

from agents.ai.fake_provider import FakeAIProvider
from core.entities.extracted_content import ExtractedContent
from core.entities.news_candidate import EstadoNewsCandidate, NewsCandidate
from core.ports.ai_provider import AIProviderError
from core.ports.cms_publisher import CategoriaCMS, CMSDraftResult
from core.services.candidate_draft_service import (
    BorradorDesdeCandidatoError,
    crear_borrador_desde_candidato,
)


class _FakeCMS:
    def __init__(self) -> None:
        self.contenido: dict[str, Any] | None = None
        self.llamadas_create = 0

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        self.llamadas_create += 1
        self.contenido = content
        return CMSDraftResult(post_id="77", url="https://www.portalvallenato.com/?p=77")

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


def test_rejects_an_already_procesado_candidate() -> None:
    with pytest.raises(ValueError):
        crear_borrador_desde_candidato(
            _candidato(estado=EstadoNewsCandidate.PROCESADO), FakeAIProvider(), _FakeCMS()
        )
