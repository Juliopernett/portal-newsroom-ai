"""Unit tests for core.services.metricas_service and MetricasPost."""

from __future__ import annotations

import pytest

from core.entities.destino_publicacion import CanalPublicacion
from core.entities.metrica_publicacion import MetricaPublicacion, MetricasPost
from core.services.metricas_service import FilaMetrica, resumir


def _fila(metricas: MetricasPost | None, canal: CanalPublicacion = CanalPublicacion.FACEBOOK):
    return FilaMetrica(
        destino_id="d",
        solicitud_id="s",
        titulo="t",
        canal=canal,
        url=None,
        tiene_meta_post_id=True,
        metrica=(
            MetricaPublicacion(destino_id="d", canal=canal, metricas=metricas)
            if metricas is not None
            else None
        ),
    )


def test_interacciones_sums_only_what_is_known() -> None:
    assert MetricasPost(reacciones=10, comentarios=2, guardados=None).interacciones == 12
    assert MetricasPost().interacciones is None


def test_negative_counters_are_rejected() -> None:
    with pytest.raises(ValueError):
        MetricasPost(alcance=-1)


def test_resumen_sums_posts_with_data_and_counts_the_rest() -> None:
    filas = [
        _fila(MetricasPost(alcance=100, vistas=150, reacciones=10, comentarios=5)),
        _fila(MetricasPost(alcance=50, reacciones=1), CanalPublicacion.INSTAGRAM),
        _fila(None),
    ]

    r = resumir(filas)

    assert (r.publicaciones_total, r.publicaciones_con_datos, r.publicaciones_sin_datos) == (3, 2, 1)
    assert r.alcance_total == 150
    assert r.vistas_total == 150  # the post without views is skipped, not counted as 0
    assert r.interacciones_total == 16


def test_resumen_without_any_data_reports_none_not_zero() -> None:
    r = resumir([_fila(None), _fila(MetricasPost())])

    assert r.alcance_total is None and r.interacciones_total is None
    assert r.publicaciones_con_datos == 0


def test_metrica_publicacion_rejects_wordpress() -> None:
    with pytest.raises(ValueError):
        MetricaPublicacion(
            destino_id="d", canal=CanalPublicacion.WORDPRESS, metricas=MetricasPost()
        )
