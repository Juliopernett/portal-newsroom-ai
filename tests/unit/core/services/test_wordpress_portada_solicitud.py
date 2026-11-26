"""The Solicitudes draft can render the branded cover, like the Radar's "Crear noticia"."""

from __future__ import annotations

from typing import Any

from core.ports.cms_publisher import CMSDraftResult, MediaSubidaCMS
from core.ports.portada_renderer import SolicitudPortada
from core.services.candidate_draft_service import PortadaParaBorrador
from core.services.wordpress_publication_service import (
    clave_portada_solicitud,
    preparar_y_crear_borrador,
)
from tests.unit.core.services.test_wordpress_publication_service import (
    _destino,
    _FakeAIProvider,
    _FakeCMSPublisher,
    _FakeMediaStorage,
    _imagen,
    _solicitud,
)


class _CMSConPortada(_FakeCMSPublisher):
    def __init__(self) -> None:
        super().__init__(resultado=CMSDraftResult(post_id="1", url="https://example.com/?p=1"))
        self.subidas: list[tuple[str, bytes]] = []
        self.textos_alternativos: list[str] = []

    def subir_media_con_url(
        self, contenido: bytes, nombre: str, content_type: str, texto_alternativo: str
    ) -> MediaSubidaCMS:
        self.subidas.append((nombre, contenido))
        self.textos_alternativos.append(texto_alternativo)
        return MediaSubidaCMS(id="media-9", url="https://example.com/portada.jpg")


class _Renderer:
    def __init__(self) -> None:
        self.pedida: SolicitudPortada | None = None

    def renderizar(self, solicitud: SolicitudPortada, *, formato: str = "png") -> bytes:
        self.pedida = solicitud
        return b"portada-jpeg"


def _crear(portada: PortadaParaBorrador | None, **extra: Any) -> tuple[Any, ...]:
    cms, renderer, storage = _CMSConPortada(), _Renderer(), _FakeMediaStorage()
    solicitud = _solicitud(id="s1")
    preparar_y_crear_borrador(
        _destino(publication_request_id="s1"),
        solicitud,
        extra.get("media", []),
        _FakeAIProvider(),
        cms,
        storage,
        portada=portada,
        portada_renderer=renderer,
        descripcion_foto=extra.get("descripcion"),
    )
    return cms, renderer, storage


def test_portada_becomes_the_featured_image_and_is_kept_for_download() -> None:
    cms, renderer, storage = _crear(PortadaParaBorrador(imagen_base=b"foto"))

    assert cms.contenido_recibido["featured_media"] == "media-9"
    assert cms.subidas == [("portada-titular-generado.jpg", b"portada-jpeg")]
    assert storage.leer(clave_portada_solicitud("s1")) == b"portada-jpeg"
    # No headline chosen: the cover uses the draft's own title (the AI's).
    assert renderer.pedida is not None and renderer.pedida.titular == "Titular generado"


def test_chosen_headline_wins_and_cover_replaces_the_attached_image() -> None:
    cms, renderer, _ = _crear(
        PortadaParaBorrador(imagen_base=b"foto", titular="Titular mío"),
        media=[_imagen(publication_request_id="s1")],
    )

    assert renderer.pedida is not None and renderer.pedida.titular == "Titular mío"
    assert cms.contenido_recibido["featured_media"] == "media-9"
    assert cms.media_subida == []  # the attached photo was not uploaded as well


def test_without_portada_nothing_changes() -> None:
    cms, renderer, storage = _crear(None)

    assert "featured_media" not in cms.contenido_recibido
    assert renderer.pedida is None
    try:
        storage.leer(clave_portada_solicitud("s1"))
    except FileNotFoundError:
        pass
    else:  # pragma: no cover
        raise AssertionError("no cover should be stored")


def test_photo_description_is_the_alt_text() -> None:
    cms, _, _ = _crear(
        PortadaParaBorrador(imagen_base=b"foto"), descripcion="  Cantante   en tarima "
    )

    assert cms.textos_alternativos == ["Cantante en tarima"]


def test_without_description_the_alt_text_is_the_draft_title() -> None:
    cms, _, _ = _crear(PortadaParaBorrador(imagen_base=b"foto"), descripcion="   ")

    assert cms.textos_alternativos == ["Titular generado"]


def test_the_framing_reaches_the_renderer() -> None:
    _, renderer, _ = _crear(
        PortadaParaBorrador(imagen_base=b"foto", enfoque_x=0.2, enfoque_y=0.8, zoom=1.5)
    )

    pedida = renderer.pedida
    assert pedida is not None
    assert (pedida.enfoque_x, pedida.enfoque_y, pedida.zoom) == (0.2, 0.8, 1.5)
