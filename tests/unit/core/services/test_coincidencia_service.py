"""Unit tests for coincidencia_service — pure, no I/O."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.services.coincidencia_service import calcular_coincidencia

_FECHA = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)


def _score(**overrides: object) -> float:
    defaults: dict[str, object] = {
        "solicitud_titulo": None,
        "solicitud_texto": "Alex Martínez presenta su nueva canción con todo el sabor vallenato",
        "solicitud_cliente_nombre": "Alex Martínez",
        "solicitud_fecha_recepcion": _FECHA,
        "post_texto": "Alex Martínez presenta su nueva canción 🎶🔥",
        "post_fecha_publicacion": _FECHA,
    }
    defaults.update(overrides)
    return calcular_coincidencia(**defaults)  # type: ignore[arg-type]


def test_strong_match_scores_high() -> None:
    assert _score() > 0.8


def test_unrelated_post_scores_low() -> None:
    resultado = _score(
        solicitud_texto="Alex Martínez presenta su nueva canción con todo el sabor vallenato",
        solicitud_cliente_nombre="Alex Martínez",
        post_texto="Feliz cumpleaños a nuestro querido equipo de producción 🎉",
        post_fecha_publicacion=_FECHA + timedelta(days=15),
    )

    assert resultado < 0.2


def test_titulo_contributes_alongside_texto() -> None:
    con_titulo = _score(
        solicitud_titulo="Lanzamiento La Solterita 3000",
        solicitud_texto="contenido genérico sin relación",
        post_texto="Ya está disponible La Solterita 3000",
    )
    sin_titulo = _score(
        solicitud_titulo=None,
        solicitud_texto="contenido genérico sin relación",
        post_texto="Ya está disponible La Solterita 3000",
    )

    assert con_titulo > sin_titulo


def test_cliente_nombre_ausente_no_rompe_el_calculo() -> None:
    resultado = _score(solicitud_cliente_nombre=None)

    assert 0.0 <= resultado <= 1.0


def test_fecha_lejana_reduce_el_puntaje() -> None:
    cercana = _score(post_fecha_publicacion=_FECHA)
    lejana = _score(post_fecha_publicacion=_FECHA + timedelta(days=30))

    assert lejana < cercana


def test_fecha_dentro_de_la_ventana_aun_contribuye() -> None:
    mismo_dia = _score(post_fecha_publicacion=_FECHA)
    dos_dias_despues = _score(post_fecha_publicacion=_FECHA + timedelta(days=2))

    assert dos_dias_despues < mismo_dia
    assert dos_dias_despues > 0.0


def test_score_siempre_entre_0_y_1() -> None:
    resultado = _score(
        solicitud_titulo="x" * 500,
        solicitud_texto="y" * 500,
        post_texto="x" * 500 + "y" * 500,
        post_fecha_publicacion=_FECHA,
    )

    assert 0.0 <= resultado <= 1.0


def test_textos_vacios_no_rompen_el_calculo() -> None:
    resultado = calcular_coincidencia(
        solicitud_titulo=None,
        solicitud_texto="a",
        solicitud_cliente_nombre=None,
        solicitud_fecha_recepcion=_FECHA,
        post_texto="",
        post_fecha_publicacion=_FECHA,
    )

    assert 0.0 <= resultado <= 1.0
