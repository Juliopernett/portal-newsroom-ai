"""Unit tests for wordpress_publication_service — no network, fake CMSPublisher."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.entities.media_asset import MediaAsset, MediaAssetType
from core.entities.publication_request import EstadoPreparacionIA, PublicationRequest
from core.ports.ai_provider import AIProviderError
from core.ports.cms_publisher import CategoriaCMS, CMSDraftResult, ConsultaPostCMS, EstadoPostCMS
from core.services.wordpress_publication_service import (
    construir_contenido_wordpress,
    crear_borrador,
    preparar_y_crear_borrador,
)

_RESPUESTA_IA_VALIDA = json.dumps(
    {
        "titulo": "Titular generado",
        "entradilla": "Entradilla generada.",
        "contenido": "Cuerpo reescrito.",
        "categoria": "Noticias",
        "etiquetas": ["vallenato"],
        "slug": "titular-generado",
    }
)


class _FakeCMSPublisher:
    """In-memory CMSPublisher — records the content it received, no network."""

    def __init__(
        self,
        resultado: CMSDraftResult | None = None,
        categorias: list[CategoriaCMS] | None = None,
        error_create_draft: Exception | None = None,
    ) -> None:
        self.resultado = resultado
        self.categorias = categorias or []
        self.error_create_draft = error_create_draft
        self.contenido_recibido: dict[str, Any] | None = None
        self.etiquetas_resueltas: list[str] = []
        self.media_subida: list[tuple[str, str, int]] = []

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:
        if self.error_create_draft is not None:
            raise self.error_create_draft
        self.contenido_recibido = content
        assert self.resultado is not None
        return self.resultado

    def listar_categorias(self) -> list[CategoriaCMS]:
        return self.categorias

    def resolver_o_crear_etiqueta(self, nombre: str) -> str:
        self.etiquetas_resueltas.append(nombre)
        return f"tag-{nombre}"

    def subir_media(self, contenido: bytes, nombre_archivo: str, content_type: str) -> str:
        self.media_subida.append((nombre_archivo, content_type, len(contenido)))
        return "media-1"

    def consultar_estado_post(self, post_id: str) -> ConsultaPostCMS:
        return ConsultaPostCMS(estado=EstadoPostCMS.BORRADOR, url=None, fecha_publicacion=None)


class _FakeAIProvider:
    """In-memory AIProvider — returns a canned structured response, or raises."""

    def __init__(self, respuesta: str | None = _RESPUESTA_IA_VALIDA, error: Exception | None = None) -> None:
        self._respuesta = respuesta
        self._error = error

    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_structured(self, prompt: str, json_schema: dict[str, Any]) -> str:
        if self._error is not None:
            raise self._error
        assert self._respuesta is not None
        return self._respuesta


class _FakeMediaStorage:
    """In-memory MediaStorage — no disk, no network."""

    def __init__(self, contenidos: dict[str, bytes] | None = None) -> None:
        self._contenidos = dict(contenidos or {})

    def guardar(self, key: str, contenido: bytes) -> None:
        self._contenidos[key] = contenido

    def leer(self, key: str) -> bytes:
        if key not in self._contenidos:
            raise FileNotFoundError(key)
        return self._contenidos[key]

    def eliminar(self, key: str) -> None:
        self._contenidos.pop(key, None)


def _solicitud(**overrides: object) -> PublicationRequest:
    defaults: dict[str, object] = {"texto": "Anuncio de nueva canción"}
    defaults.update(overrides)
    return PublicationRequest(**defaults)


def _destino(**overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {
        "publication_request_id": "solicitud-1",
        "canal": CanalPublicacion.WORDPRESS,
    }
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def _imagen(**overrides: object) -> MediaAsset:
    defaults: dict[str, object] = {
        "publication_request_id": "solicitud-1",
        "tipo": MediaAssetType.IMAGEN,
        "nombre_archivo": "foto.jpg",
        "content_type": "image/jpeg",
        "tamano_bytes": 3,
        "storage_key": "solicitud-1/foto.jpg",
    }
    defaults.update(overrides)
    return MediaAsset(**defaults)


# --- construir_contenido_wordpress ---


def test_construir_contenido_uses_titulo_when_present() -> None:
    solicitud = _solicitud(titulo="Lanzamiento del sencillo", texto="Texto largo del comunicado")

    contenido = construir_contenido_wordpress(solicitud)

    assert contenido == {
        "title": "Lanzamiento del sencillo",
        "content": "Texto largo del comunicado",
    }


def test_construir_contenido_falls_back_to_texto_prefix_when_no_titulo() -> None:
    texto_largo = "x" * 100
    solicitud = _solicitud(texto=texto_largo)

    contenido = construir_contenido_wordpress(solicitud)

    assert contenido["title"] == texto_largo[:60]
    assert contenido["content"] == texto_largo


def test_construir_contenido_prefers_editorial_fields_when_procesado() -> None:
    solicitud = _solicitud(
        texto="Texto crudo",
        contenido_editorial="Cuerpo reescrito",
        titulo_editorial="Titular IA",
        entradilla_editorial="Entradilla IA",
        slug_editorial="titular-ia",
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
    )

    contenido = construir_contenido_wordpress(solicitud)

    assert contenido["title"] == "Titular IA"
    assert contenido["content"] == "Cuerpo reescrito"
    assert contenido["excerpt"] == "Entradilla IA"
    assert contenido["slug"] == "titular-ia"


def test_construir_contenido_operador_titulo_wins_over_titulo_editorial() -> None:
    solicitud = _solicitud(
        titulo="Título del operador",
        contenido_editorial="Cuerpo reescrito",
        titulo_editorial="Titular IA",
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
    )

    contenido = construir_contenido_wordpress(solicitud)

    assert contenido["title"] == "Título del operador"


def test_construir_contenido_includes_yoast_meta_when_seo_fields_set() -> None:
    solicitud = _solicitud(
        contenido_editorial="Cuerpo reescrito",
        titulo_editorial="Titular IA",
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
        meta_titulo_editorial="Meta título SEO",
        meta_descripcion_editorial="Meta descripción SEO.",
        frase_clave_editorial="frase clave",
    )

    contenido = construir_contenido_wordpress(solicitud)

    assert contenido["meta"] == {
        "_yoast_wpseo_title": "Meta título SEO",
        "_yoast_wpseo_metadesc": "Meta descripción SEO.",
        "_yoast_wpseo_focuskw": "frase clave",
    }


def test_construir_contenido_omits_meta_when_no_seo_fields_set() -> None:
    solicitud = _solicitud(
        contenido_editorial="Cuerpo reescrito",
        titulo_editorial="Titular IA",
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
    )

    contenido = construir_contenido_wordpress(solicitud)

    assert "meta" not in contenido


def test_construir_contenido_ignores_editorial_fields_when_fallido() -> None:
    solicitud = _solicitud(
        texto="Texto crudo",
        preparacion_ia_estado=EstadoPreparacionIA.FALLIDO,
        preparacion_ia_error="la IA no respondió",
    )

    contenido = construir_contenido_wordpress(solicitud)

    assert contenido == {"title": "Texto crudo", "content": "Texto crudo"}


# --- crear_borrador ---


def test_crear_borrador_attaches_post_id_and_url() -> None:
    destino = _destino()
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="42", url="https://example.com/?p=42"))

    resultado = crear_borrador(destino, {"title": "T", "content": "C"}, publisher)

    assert resultado.wp_post_id == "42"
    assert resultado.wp_url == "https://example.com/?p=42"


def test_crear_borrador_keeps_estado_pendiente() -> None:
    destino = _destino()
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    resultado = crear_borrador(destino, {"title": "T", "content": "C"}, publisher)

    assert resultado.estado == EstadoDestino.PENDIENTE


def test_crear_borrador_does_not_mutate_the_original_destino() -> None:
    destino = _destino()
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    crear_borrador(destino, {"title": "T", "content": "C"}, publisher)

    assert destino.wp_post_id is None


def test_crear_borrador_passes_content_to_the_publisher_unchanged() -> None:
    destino = _destino()
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    crear_borrador(destino, {"title": "Titulo", "content": "Cuerpo"}, publisher)

    assert publisher.contenido_recibido == {"title": "Titulo", "content": "Cuerpo"}


@pytest.mark.parametrize("canal", [CanalPublicacion.FACEBOOK, CanalPublicacion.INSTAGRAM])
def test_crear_borrador_rejects_non_wordpress_canal(canal: CanalPublicacion) -> None:
    destino = _destino(canal=canal)
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    with pytest.raises(ValueError, match="wordpress"):
        crear_borrador(destino, {"title": "T", "content": "C"}, publisher)


def test_crear_borrador_rejects_a_cancelado_destino() -> None:
    destino = _destino(estado=EstadoDestino.CANCELADO)
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    with pytest.raises(ValueError, match="terminal"):
        crear_borrador(destino, {"title": "T", "content": "C"}, publisher)


def test_crear_borrador_rejects_a_publicado_destino() -> None:
    destino = _destino(
        estado=EstadoDestino.PUBLICADO, fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC)
    )
    publisher = _FakeCMSPublisher(CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    with pytest.raises(ValueError, match="terminal"):
        crear_borrador(destino, {"title": "T", "content": "C"}, publisher)


# --- preparar_y_crear_borrador ---


def test_preparar_y_crear_borrador_uses_editorial_content_on_ai_success() -> None:
    solicitud = _solicitud(texto="Texto crudo")
    destino = _destino()
    publisher = _FakeCMSPublisher(
        resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1"),
        categorias=[CategoriaCMS(id="7", nombre="Noticias")],
    )

    con_borrador, solicitud_actualizada = preparar_y_crear_borrador(
        destino, solicitud, [], _FakeAIProvider(), publisher, _FakeMediaStorage()
    )

    assert con_borrador.wp_post_id == "1"
    assert solicitud_actualizada.preparacion_ia_estado == EstadoPreparacionIA.PROCESADO
    assert publisher.contenido_recibido is not None
    assert publisher.contenido_recibido["title"] == "Titular generado"
    assert publisher.contenido_recibido["content"] == "Cuerpo reescrito."
    assert publisher.contenido_recibido["categories"] == ["7"]
    assert publisher.etiquetas_resueltas == ["vallenato"]


def test_preparar_y_crear_borrador_discards_blank_etiquetas_before_resolving() -> None:
    """Reproduced live (2026-08-25): a blank etiqueta reaching WordPress raises
    `400 empty_term_name` and aborts the whole draft — must be filtered out
    before ever calling `resolver_o_crear_etiqueta`."""
    solicitud = _solicitud(
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
        titulo_editorial="Titular",
        contenido_editorial="Cuerpo.",
        etiquetas_editorial=("vallenato", "", "   ", "Karen Lizarazo"),
    )
    destino = _destino()
    publisher = _FakeCMSPublisher(resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1"))

    preparar_y_crear_borrador(destino, solicitud, [], _FakeAIProvider(), publisher, _FakeMediaStorage())

    assert publisher.etiquetas_resueltas == ["vallenato", "Karen Lizarazo"]


def test_preparar_y_crear_borrador_omits_category_when_no_match() -> None:
    solicitud = _solicitud()
    destino = _destino()
    publisher = _FakeCMSPublisher(
        resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1"),
        categorias=[CategoriaCMS(id="9", nombre="Otra categoría totalmente distinta")],
    )

    preparar_y_crear_borrador(
        destino, solicitud, [], _FakeAIProvider(), publisher, _FakeMediaStorage()
    )

    assert publisher.contenido_recibido is not None
    assert "categories" not in publisher.contenido_recibido


def test_preparar_y_crear_borrador_falls_back_to_raw_texto_when_ai_fails() -> None:
    solicitud = _solicitud(texto="Texto crudo original")
    destino = _destino()
    publisher = _FakeCMSPublisher(
        resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1")
    )
    provider = _FakeAIProvider(error=AIProviderError("ANTHROPIC_API_KEY no configurado"))

    con_borrador, solicitud_actualizada = preparar_y_crear_borrador(
        destino, solicitud, [], provider, publisher, _FakeMediaStorage()
    )

    # the draft is still created — an AI outage never blocks WordPress
    assert con_borrador.wp_post_id == "1"
    assert publisher.contenido_recibido == {
        "title": "Texto crudo original",
        "content": "Texto crudo original",
    }
    assert solicitud_actualizada.preparacion_ia_estado == EstadoPreparacionIA.FALLIDO
    assert solicitud_actualizada.preparacion_ia_error is not None
    assert "ANTHROPIC_API_KEY" in solicitud_actualizada.preparacion_ia_error
    # the original texto is never touched
    assert solicitud_actualizada.texto == "Texto crudo original"


def test_preparar_y_crear_borrador_skips_ai_when_already_procesado() -> None:
    solicitud = _solicitud(
        texto="Texto crudo",
        contenido_editorial="Ya reescrito antes",
        titulo_editorial="Titular ya generado",
        preparacion_ia_estado=EstadoPreparacionIA.PROCESADO,
    )
    destino = _destino()
    publisher = _FakeCMSPublisher(
        resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1")
    )

    def _boom(prompt: str, schema: dict[str, Any]) -> str:  # pragma: no cover - must not run
        raise AssertionError("no debería volver a llamar a la IA")

    class _FailingProvider:
        def generate(self, prompt: str) -> str:
            raise AssertionError

        def generate_structured(self, prompt: str, json_schema: dict[str, Any]) -> str:
            return _boom(prompt, json_schema)

    preparar_y_crear_borrador(
        destino, solicitud, [], _FailingProvider(), publisher, _FakeMediaStorage()
    )

    assert publisher.contenido_recibido is not None
    assert publisher.contenido_recibido["title"] == "Titular ya generado"


def test_preparar_y_crear_borrador_attaches_the_earliest_imagen() -> None:
    solicitud = _solicitud()
    destino = _destino()
    publisher = _FakeCMSPublisher(
        resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1")
    )
    mas_vieja = _imagen(
        id="img-1",
        nombre_archivo="vieja.jpg",
        storage_key="solicitud-1/vieja.jpg",
        fecha_subida=datetime(2026, 1, 1, tzinfo=UTC),
    )
    mas_nueva = _imagen(
        id="img-2",
        nombre_archivo="nueva.jpg",
        storage_key="solicitud-1/nueva.jpg",
        fecha_subida=datetime(2026, 2, 1, tzinfo=UTC),
    )
    storage = _FakeMediaStorage({mas_vieja.storage_key: b"foto", mas_nueva.storage_key: b"foto2"})

    preparar_y_crear_borrador(
        destino, solicitud, [mas_nueva, mas_vieja], _FakeAIProvider(), publisher, storage
    )

    assert publisher.media_subida == [("vieja.jpg", "image/jpeg", 4)]
    assert publisher.contenido_recibido is not None
    assert publisher.contenido_recibido["featured_media"] == "media-1"


def test_preparar_y_crear_borrador_skips_featured_image_when_none_attached() -> None:
    solicitud = _solicitud()
    destino = _destino()
    publisher = _FakeCMSPublisher(
        resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1")
    )

    preparar_y_crear_borrador(
        destino, solicitud, [], _FakeAIProvider(), publisher, _FakeMediaStorage()
    )

    assert publisher.contenido_recibido is not None
    assert "featured_media" not in publisher.contenido_recibido


def test_preparar_y_crear_borrador_skips_missing_media_file_without_failing() -> None:
    solicitud = _solicitud()
    destino = _destino()
    publisher = _FakeCMSPublisher(
        resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1")
    )
    imagen = _imagen()

    con_borrador, _ = preparar_y_crear_borrador(
        destino, solicitud, [imagen], _FakeAIProvider(), publisher, _FakeMediaStorage()
    )

    assert con_borrador.wp_post_id == "1"
    assert publisher.contenido_recibido is not None
    assert "featured_media" not in publisher.contenido_recibido


def test_preparar_y_crear_borrador_propagates_wordpress_failure_uncaught() -> None:
    solicitud = _solicitud()
    destino = _destino()
    publisher = _FakeCMSPublisher(error_create_draft=RuntimeError("WordPress no responde"))

    with pytest.raises(RuntimeError, match="WordPress no responde"):
        preparar_y_crear_borrador(
            destino, solicitud, [], _FakeAIProvider(), publisher, _FakeMediaStorage()
        )
