"""Unit tests for core.services.source_resolution_service — fakes, no I/O."""

from __future__ import annotations

import pytest

from core.entities.extracted_content import ExtractedContent
from core.entities.news_candidate import EstadoResolucionFuente, NewsCandidate
from core.ports.content_extractor import ContentExtractorError
from core.ports.source_resolver import ResolvedSource
from core.services.source_resolution_service import (
    preparar_contenido,
    preparar_noticia,
    resolver_fuente,
)


class _FakeSourceResolver:
    def __init__(self, resultado: ResolvedSource) -> None:
        self._resultado = resultado
        self.llamado_con: str | None = None

    def resolve(self, url: str) -> ResolvedSource:
        self.llamado_con = url
        return self._resultado


class _FakeContentExtractor:
    def __init__(
        self, contenido: ExtractedContent | None = None, error: Exception | None = None
    ) -> None:
        self._contenido = contenido
        self._error = error
        self.llamado_con: str | None = None

    def extract(self, reference: str) -> ExtractedContent:
        self.llamado_con = reference
        if self._error is not None:
            raise self._error
        assert self._contenido is not None
        return self._contenido


def _build_candidate(**overrides: object) -> NewsCandidate:
    defaults: dict[str, object] = {
        "source": "radar-google-news-vallenato",
        "title": "Un festival vallenato bate récord de asistencia",
        "url": "https://news.google.com/rss/articles/CBMi123",
        "summary": "Miles de personas asistieron.",
        "hash": "abc123",
    }
    defaults.update(overrides)
    return NewsCandidate(**defaults)


def _extracted_content(**overrides: object) -> ExtractedContent:
    defaults: dict[str, object] = {
        "title": "Un festival vallenato bate récord de asistencia",
        "body": "Cuerpo completo de la noticia.",
        "source_url": "https://elpilon.com.co/festival-record",
    }
    defaults.update(overrides)
    return ExtractedContent(**defaults)


# --- resolver_fuente ---


def test_resolver_fuente_marks_candidate_resuelta_on_success() -> None:
    candidato = _build_candidate()
    resolver = _FakeSourceResolver(
        ResolvedSource(success=True, resolved_url="https://elpilon.com.co/festival-record")
    )

    actualizado = resolver_fuente(candidato, resolver)

    assert actualizado.estado_resolucion == EstadoResolucionFuente.RESUELTA
    assert actualizado.url_fuente_original == "https://elpilon.com.co/festival-record"
    assert resolver.llamado_con == candidato.url


def test_resolver_fuente_marks_candidate_fallida_on_failure() -> None:
    candidato = _build_candidate()
    resolver = _FakeSourceResolver(
        ResolvedSource(success=False, resolved_url=None, error="timeout")
    )

    actualizado = resolver_fuente(candidato, resolver)

    assert actualizado.estado_resolucion == EstadoResolucionFuente.FALLIDA
    assert actualizado.url_fuente_original is None


def test_resolver_fuente_never_loses_the_candidate_on_failure() -> None:
    """A failed resolution returns a candidate, never raises."""
    candidato = _build_candidate()
    resolver = _FakeSourceResolver(ResolvedSource(success=False, resolved_url=None, error="x"))

    actualizado = resolver_fuente(candidato, resolver)

    assert actualizado.id == candidato.id
    assert actualizado.title == candidato.title


# --- preparar_contenido ---


def test_preparar_contenido_requires_a_resolved_candidate() -> None:
    candidato = _build_candidate()  # estado_resolucion still PENDIENTE
    extractor = _FakeContentExtractor(contenido=_extracted_content())

    with pytest.raises(ValueError, match="fuente resuelta"):
        preparar_contenido(candidato, extractor)


def test_preparar_contenido_populates_extracted_content_on_success() -> None:
    candidato = _build_candidate(
        estado_resolucion=EstadoResolucionFuente.RESUELTA,
        url_fuente_original="https://elpilon.com.co/festival-record",
    )
    contenido = _extracted_content()
    extractor = _FakeContentExtractor(contenido=contenido)

    actualizado = preparar_contenido(candidato, extractor)

    assert actualizado.extracted_content == contenido
    assert extractor.llamado_con == "https://elpilon.com.co/festival-record"


def test_preparar_contenido_never_raises_on_extraction_failure() -> None:
    candidato = _build_candidate(
        estado_resolucion=EstadoResolucionFuente.RESUELTA,
        url_fuente_original="https://elpilon.com.co/festival-record",
    )
    extractor = _FakeContentExtractor(error=ContentExtractorError("sin contenido reconocible"))

    actualizado = preparar_contenido(candidato, extractor)

    assert actualizado.extracted_content is None
    assert actualizado.id == candidato.id


# --- preparar_noticia (composición) ---


def test_preparar_noticia_resolves_then_extracts_on_success() -> None:
    candidato = _build_candidate()
    resolver = _FakeSourceResolver(
        ResolvedSource(success=True, resolved_url="https://elpilon.com.co/festival-record")
    )
    contenido = _extracted_content()
    extractor = _FakeContentExtractor(contenido=contenido)

    actualizado = preparar_noticia(candidato, resolver, extractor)

    assert actualizado.estado_resolucion == EstadoResolucionFuente.RESUELTA
    assert actualizado.extracted_content == contenido


def test_preparar_noticia_skips_extraction_when_resolution_fails() -> None:
    candidato = _build_candidate()
    resolver = _FakeSourceResolver(ResolvedSource(success=False, resolved_url=None, error="x"))
    extractor = _FakeContentExtractor(contenido=_extracted_content())

    actualizado = preparar_noticia(candidato, resolver, extractor)

    assert actualizado.estado_resolucion == EstadoResolucionFuente.FALLIDA
    assert actualizado.extracted_content is None
    assert extractor.llamado_con is None
