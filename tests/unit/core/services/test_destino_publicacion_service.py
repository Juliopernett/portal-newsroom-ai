"""Unit tests for destino_publicacion_service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from core.entities.destino_publicacion import CanalPublicacion, DestinoPublicacion, EstadoDestino
from core.ports.cms_publisher import CategoriaCMS, CMSDraftResult, ConsultaPostCMS, EstadoPostCMS
from core.services.destino_publicacion_service import (
    cancelar,
    corregir_enlace,
    esta_completa,
    marcar_fallido,
    marcar_publicado,
    puede_eliminarse_sin_afectar_completitud,
    sincronizar_estado_wordpress,
    tiene_destino_social,
)


class _FakeCMSPublisherEstado:
    """In-memory CMSPublisher stub — only `consultar_estado_post` matters here."""

    def __init__(self, consulta: ConsultaPostCMS | None = None) -> None:
        self._consulta = consulta
        self.post_id_consultado: str | None = None
        self.llamadas = 0

    def create_draft(self, content: dict[str, Any]) -> CMSDraftResult:  # pragma: no cover - unused here
        raise NotImplementedError

    def listar_categorias(self) -> list[CategoriaCMS]:  # pragma: no cover - unused here
        return []

    def resolver_o_crear_etiqueta(self, nombre: str) -> str:  # pragma: no cover - unused here
        raise NotImplementedError

    def subir_media(self, contenido: bytes, nombre_archivo: str, content_type: str) -> str:
        raise NotImplementedError  # pragma: no cover - unused here

    def consultar_estado_post(self, post_id: str) -> ConsultaPostCMS:
        self.llamadas += 1
        self.post_id_consultado = post_id
        assert self._consulta is not None
        return self._consulta


def _destino(**overrides: object) -> DestinoPublicacion:
    defaults: dict[str, object] = {
        "publication_request_id": "solicitud-1",
        "canal": CanalPublicacion.WORDPRESS,
    }
    defaults.update(overrides)
    return DestinoPublicacion(**defaults)


def test_marcar_publicado_transitions_status() -> None:
    destino = _destino()

    resultado = marcar_publicado(destino, registrado_por_user_id="user-1")

    assert resultado.estado == EstadoDestino.PUBLICADO
    assert resultado.registrado_por_user_id == "user-1"
    assert isinstance(resultado.fecha_publicacion, datetime)


def test_marcar_publicado_does_not_mutate_the_original() -> None:
    destino = _destino()

    marcar_publicado(destino)

    assert destino.estado == EstadoDestino.PENDIENTE


def test_marcar_publicado_accepts_explicit_fecha_publicacion() -> None:
    destino = _destino()
    fecha = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)

    resultado = marcar_publicado(destino, fecha_publicacion=fecha)

    assert resultado.fecha_publicacion == fecha


def test_marcar_publicado_sets_wordpress_fields() -> None:
    destino = _destino(canal=CanalPublicacion.WORDPRESS)

    resultado = marcar_publicado(destino, wp_post_id="42", wp_url="https://example.com/?p=42")

    assert resultado.wp_post_id == "42"
    assert resultado.wp_url == "https://example.com/?p=42"


def test_marcar_publicado_sets_url_publicacion_for_social_channel() -> None:
    destino = _destino(canal=CanalPublicacion.FACEBOOK)

    resultado = marcar_publicado(destino, url_publicacion="https://facebook.com/post/1")

    assert resultado.url_publicacion == "https://facebook.com/post/1"


def test_marcar_publicado_sets_meta_post_id_when_given() -> None:
    destino = _destino(canal=CanalPublicacion.FACEBOOK)

    resultado = marcar_publicado(
        destino, url_publicacion="https://facebook.com/post/1", meta_post_id="123_456"
    )

    assert resultado.meta_post_id == "123_456"


def test_marcar_publicado_leaves_meta_post_id_none_when_not_given() -> None:
    """A manually-typed link (not picked from the posts-recientes picker)
    never gets a meta_post_id — it was never associated with a real Meta
    id in the first place."""
    destino = _destino(canal=CanalPublicacion.FACEBOOK)

    resultado = marcar_publicado(destino, url_publicacion="https://facebook.com/post/1")

    assert resultado.meta_post_id is None


def test_marcar_publicado_allows_retry_from_fallido() -> None:
    destino = _destino(estado=EstadoDestino.FALLIDO, ultimo_error="timeout")

    resultado = marcar_publicado(destino)

    assert resultado.estado == EstadoDestino.PUBLICADO


@pytest.mark.parametrize(
    "estado",
    [EstadoDestino.CANCELADO],
)
def test_marcar_publicado_rejects_terminal_destino(estado: EstadoDestino) -> None:
    destino = _destino(estado=estado)

    with pytest.raises(ValueError, match="terminal"):
        marcar_publicado(destino)


def test_marcar_publicado_rejects_already_published_destino() -> None:
    destino = _destino(
        estado=EstadoDestino.PUBLICADO, fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC)
    )

    with pytest.raises(ValueError, match="terminal"):
        marcar_publicado(destino)


def test_marcar_fallido_transitions_status_and_records_error() -> None:
    destino = _destino()

    resultado = marcar_fallido(destino, error="WordPress no respondió")

    assert resultado.estado == EstadoDestino.FALLIDO
    assert resultado.ultimo_error == "WordPress no respondió"


def test_marcar_fallido_rejects_terminal_destino() -> None:
    destino = _destino(estado=EstadoDestino.CANCELADO)

    with pytest.raises(ValueError, match="terminal"):
        marcar_fallido(destino, error="no importa")


def test_cancelar_transitions_status() -> None:
    destino = _destino()

    resultado = cancelar(destino)

    assert resultado.estado == EstadoDestino.CANCELADO


def test_cancelar_allows_cancelling_a_failed_destino() -> None:
    destino = _destino(estado=EstadoDestino.FALLIDO, ultimo_error="timeout")

    resultado = cancelar(destino)

    assert resultado.estado == EstadoDestino.CANCELADO


def test_cancelar_rejects_an_already_published_destino() -> None:
    destino = _destino(
        estado=EstadoDestino.PUBLICADO, fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC)
    )

    with pytest.raises(ValueError, match="publicado"):
        cancelar(destino)


def test_corregir_enlace_replaces_url_publicacion_on_a_published_destino() -> None:
    destino = _destino(
        canal=CanalPublicacion.INSTAGRAM,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
        url_publicacion="https://instagram.com/p/wrong",
    )

    resultado = corregir_enlace(destino, url_publicacion="https://instagram.com/p/correct")

    assert resultado.url_publicacion == "https://instagram.com/p/correct"


def test_corregir_enlace_replaces_wp_url_on_a_published_destino() -> None:
    destino = _destino(
        canal=CanalPublicacion.WORDPRESS,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
        wp_url="https://portalvallenato.com/?p=1",
    )

    resultado = corregir_enlace(destino, wp_url="https://portalvallenato.com/?p=2")

    assert resultado.wp_url == "https://portalvallenato.com/?p=2"


def test_corregir_enlace_does_not_touch_estado_or_fecha_publicacion() -> None:
    fecha = datetime(2026, 8, 6, tzinfo=UTC)
    destino = _destino(
        canal=CanalPublicacion.INSTAGRAM,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=fecha,
        url_publicacion="https://instagram.com/p/wrong",
    )

    resultado = corregir_enlace(destino, url_publicacion="https://instagram.com/p/correct")

    assert resultado.estado == EstadoDestino.PUBLICADO
    assert resultado.fecha_publicacion == fecha


def test_corregir_enlace_does_not_mutate_the_original() -> None:
    destino = _destino(
        canal=CanalPublicacion.INSTAGRAM,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
        url_publicacion="https://instagram.com/p/wrong",
    )

    corregir_enlace(destino, url_publicacion="https://instagram.com/p/correct")

    assert destino.url_publicacion == "https://instagram.com/p/wrong"


def test_corregir_enlace_sets_meta_post_id_when_given() -> None:
    destino = _destino(
        canal=CanalPublicacion.INSTAGRAM,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
        url_publicacion="https://instagram.com/p/wrong",
    )

    resultado = corregir_enlace(
        destino, url_publicacion="https://instagram.com/p/correct", meta_post_id="789"
    )

    assert resultado.meta_post_id == "789"


def test_corregir_enlace_leaves_meta_post_id_unchanged_when_not_given() -> None:
    destino = _destino(
        canal=CanalPublicacion.INSTAGRAM,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
        url_publicacion="https://instagram.com/p/wrong",
        meta_post_id="original-id",
    )

    resultado = corregir_enlace(destino, url_publicacion="https://instagram.com/p/correct")

    assert resultado.meta_post_id == "original-id"


def test_corregir_enlace_rejects_a_destino_not_yet_publicado() -> None:
    destino = _destino(canal=CanalPublicacion.INSTAGRAM, estado=EstadoDestino.PENDIENTE)

    with pytest.raises(ValueError, match="PUBLICADO"):
        corregir_enlace(destino, url_publicacion="https://instagram.com/p/correct")


def test_corregir_enlace_rejects_url_publicacion_on_wrong_canal() -> None:
    """The entity's own __post_init__ still applies — corregir_enlace can't
    bypass "wp_url solo aplica a WORDPRESS"."""
    destino = _destino(
        canal=CanalPublicacion.WORDPRESS,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="url_publicacion only applies to"):
        corregir_enlace(destino, url_publicacion="https://instagram.com/p/correct")


def test_esta_completa_is_false_with_no_destinos() -> None:
    assert esta_completa([]) is False


def test_esta_completa_is_false_when_a_destino_is_still_pending() -> None:
    destinos = [
        _destino(canal=CanalPublicacion.WORDPRESS, estado=EstadoDestino.PENDIENTE),
    ]

    assert esta_completa(destinos) is False


def test_esta_completa_is_false_when_all_destinos_are_cancelled() -> None:
    destinos = [
        _destino(canal=CanalPublicacion.WORDPRESS, estado=EstadoDestino.CANCELADO),
        _destino(canal=CanalPublicacion.FACEBOOK, estado=EstadoDestino.CANCELADO),
    ]

    assert esta_completa(destinos) is False


def test_esta_completa_is_true_when_all_terminal_and_one_published() -> None:
    destinos = [
        _destino(
            canal=CanalPublicacion.WORDPRESS,
            estado=EstadoDestino.PUBLICADO,
            fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
        ),
        _destino(canal=CanalPublicacion.INSTAGRAM, estado=EstadoDestino.CANCELADO),
    ]

    assert esta_completa(destinos) is True


def test_puede_eliminarse_es_true_cuando_otro_destino_ya_deja_completa() -> None:
    """El caso real: WordPress publicado sin URL (placeholder de
    `publish_publication_request`) junto a un Facebook real — borrar el
    WordPress no cambia nada, Facebook por sí solo ya completaba."""
    wordpress = _destino(
        canal=CanalPublicacion.WORDPRESS,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )
    facebook = _destino(
        canal=CanalPublicacion.FACEBOOK,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
        url_publicacion="https://facebook.com/post/1",
    )

    assert puede_eliminarse_sin_afectar_completitud(wordpress, [facebook]) is True


def test_puede_eliminarse_es_false_cuando_es_el_unico_destino_publicado() -> None:
    wordpress = _destino(
        canal=CanalPublicacion.WORDPRESS,
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 6, tzinfo=UTC),
    )
    instagram_cancelado = _destino(
        canal=CanalPublicacion.INSTAGRAM, estado=EstadoDestino.CANCELADO
    )

    assert puede_eliminarse_sin_afectar_completitud(wordpress, [instagram_cancelado]) is False


def test_tiene_destino_social_es_true_con_un_facebook_pendiente() -> None:
    """Cualquier estado cuenta — no solo PUBLICADO, ver el docstring de la
    función: lo que importa es que el destino exista, no si ya se
    confirmó."""
    assert tiene_destino_social([_destino(canal=CanalPublicacion.FACEBOOK)]) is True


def test_tiene_destino_social_es_true_con_un_instagram() -> None:
    assert tiene_destino_social([_destino(canal=CanalPublicacion.INSTAGRAM)]) is True


def test_tiene_destino_social_es_false_con_solo_wordpress() -> None:
    assert tiene_destino_social([_destino(canal=CanalPublicacion.WORDPRESS)]) is False


def test_tiene_destino_social_es_false_sin_destinos() -> None:
    assert tiene_destino_social([]) is False


def test_puede_eliminarse_es_true_cuando_ya_estaba_incompleta_sin_el() -> None:
    wordpress_pendiente = _destino(canal=CanalPublicacion.WORDPRESS)
    instagram_pendiente = _destino(canal=CanalPublicacion.INSTAGRAM)

    assert (
        puede_eliminarse_sin_afectar_completitud(wordpress_pendiente, [instagram_pendiente])
        is True
    )


def test_sincronizar_estado_wordpress_marca_publicado_cuando_wordpress_lo_reporta() -> None:
    destino = _destino(wp_post_id="42", wp_url="https://example.com/?p=42")
    fecha = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
    cms = _FakeCMSPublisherEstado(
        ConsultaPostCMS(
            estado=EstadoPostCMS.PUBLICADO, url="https://example.com/nota-real/", fecha_publicacion=fecha
        )
    )

    resultado = sincronizar_estado_wordpress(destino, cms)

    assert resultado.estado == EstadoDestino.PUBLICADO
    assert resultado.wp_url == "https://example.com/nota-real/"
    assert resultado.fecha_publicacion == fecha
    assert resultado.registrado_por_user_id is None


def test_sincronizar_estado_wordpress_mantiene_wp_url_si_wordpress_no_da_link() -> None:
    destino = _destino(wp_post_id="42", wp_url="https://example.com/?p=42")
    cms = _FakeCMSPublisherEstado(
        ConsultaPostCMS(estado=EstadoPostCMS.PUBLICADO, url=None, fecha_publicacion=datetime(2026, 8, 24, tzinfo=UTC))
    )

    resultado = sincronizar_estado_wordpress(destino, cms)

    assert resultado.wp_url == "https://example.com/?p=42"


def test_sincronizar_estado_wordpress_marca_fallido_cuando_esta_en_la_papelera() -> None:
    destino = _destino(wp_post_id="42", wp_url="https://example.com/?p=42")
    cms = _FakeCMSPublisherEstado(
        ConsultaPostCMS(estado=EstadoPostCMS.ELIMINADO, url=None, fecha_publicacion=None)
    )

    resultado = sincronizar_estado_wordpress(destino, cms)

    assert resultado.estado == EstadoDestino.FALLIDO
    assert resultado.ultimo_error is not None
    assert "papelera" in resultado.ultimo_error


def test_sincronizar_estado_wordpress_registra_error_sin_tocar_estado_ni_wp_url() -> None:
    """'post inexistente/error -> estado de error sin destruir información
    existente': ni el estado ni wp_url se pierden, solo se anota
    ultimo_error para dar visibilidad del intento fallido."""
    destino = _destino(wp_post_id="42", wp_url="https://example.com/?p=42")
    cms = _FakeCMSPublisherEstado(
        ConsultaPostCMS(estado=EstadoPostCMS.ERROR, url=None, fecha_publicacion=None)
    )

    resultado = sincronizar_estado_wordpress(destino, cms)

    assert resultado.estado == EstadoDestino.PENDIENTE
    assert resultado.wp_url == "https://example.com/?p=42"
    assert resultado.ultimo_error is not None


def test_sincronizar_estado_wordpress_no_cambia_nada_si_sigue_en_borrador() -> None:
    destino = _destino(wp_post_id="42", wp_url="https://example.com/?p=42")
    cms = _FakeCMSPublisherEstado(
        ConsultaPostCMS(estado=EstadoPostCMS.BORRADOR, url=None, fecha_publicacion=None)
    )

    resultado = sincronizar_estado_wordpress(destino, cms)

    assert resultado == destino


def test_sincronizar_estado_wordpress_es_no_op_sin_wp_post_id() -> None:
    """Sin wp_post_id (borrador nunca creado) no hay nada que consultar —
    ni siquiera se llama al CMS."""
    destino = _destino()
    cms = _FakeCMSPublisherEstado()

    resultado = sincronizar_estado_wordpress(destino, cms)

    assert resultado == destino
    assert cms.llamadas == 0


def test_sincronizar_estado_wordpress_es_no_op_para_canal_no_wordpress() -> None:
    destino = _destino(canal=CanalPublicacion.FACEBOOK, url_publicacion="https://facebook.com/post/1")
    cms = _FakeCMSPublisherEstado()

    resultado = sincronizar_estado_wordpress(destino, cms)

    assert resultado == destino
    assert cms.llamadas == 0


def test_sincronizar_estado_wordpress_es_no_op_si_ya_es_terminal() -> None:
    """Un destino ya PUBLICADO o CANCELADO no necesita sincronizarse —
    verificado con un fake que lanza si llega a llamarse, para probar que
    el short-circuit ocurre antes de tocar el CMS."""
    destino = _destino(
        wp_post_id="42",
        wp_url="https://example.com/?p=42",
        estado=EstadoDestino.PUBLICADO,
        fecha_publicacion=datetime(2026, 8, 24, tzinfo=UTC),
    )
    cms = _FakeCMSPublisherEstado()

    resultado = sincronizar_estado_wordpress(destino, cms)

    assert resultado == destino
    assert cms.llamadas == 0


def test_sincronizar_estado_wordpress_no_muta_el_original() -> None:
    destino = _destino(wp_post_id="42", wp_url="https://example.com/?p=42")
    cms = _FakeCMSPublisherEstado(
        ConsultaPostCMS(
            estado=EstadoPostCMS.PUBLICADO,
            url="https://example.com/nota-real/",
            fecha_publicacion=datetime(2026, 8, 24, tzinfo=UTC),
        )
    )

    sincronizar_estado_wordpress(destino, cms)

    assert destino.estado == EstadoDestino.PENDIENTE
