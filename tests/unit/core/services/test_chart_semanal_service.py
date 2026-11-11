"""Unit tests for the weekly editions (core.services.chart_semanal_service)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import database.models  # noqa: F401
from agents.youtube.fake_reader import FakeYouTubeReader
from core.entities.chart import ESTADO_PUBLICADA, CanalChart, CorteVistas, VideoChart
from core.ports.youtube_reader import DetalleVideo, VideoYouTube, YouTubeError
from core.services.chart_semanal_service import (
    EdicionPublicadaError,
    cerrar_semana,
    generar_edicion,
    momento_corte,
    publicar_edicion,
    semana_fin_de,
)
from database.base import Base
from database.engine import enable_sqlite_foreign_keys
from database.unit_of_work import SqlAlchemyUnitOfWork

F1 = date(2026, 11, 13)  # a Friday
F0 = F1 - timedelta(days=7)
F2 = F1 + timedelta(days=7)
CANAL = "UC" + "a" * 22
VIEJO = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def uow(tmp_path: Path) -> Iterator[SqlAlchemyUnitOfWork]:
    engine = create_engine(f"sqlite:///{tmp_path / 't.db'}")
    enable_sqlite_foreign_keys(engine)
    Base.metadata.create_all(engine)
    with SqlAlchemyUnitOfWork(sessionmaker(bind=engine)) as u:
        yield u
    engine.dispose()


def _video(uow: SqlAlchemyUnitOfWork, vid: str, publicado: datetime = VIEJO, **kw: object) -> None:
    uow.chart.save_video(
        VideoChart(
            video_id=vid,
            canal_id="UCx",
            titulo=f"Tema {vid}",
            publicado_en=publicado,
            **kw,  # type: ignore[arg-type]
        )
    )


def _corte(uow: SqlAlchemyUnitOfWork, semana: date, **vistas: int) -> None:
    for vid, v in vistas.items():
        uow.chart.save_corte(CorteVistas(vid, semana, v))


def test_week_closes_on_friday_midnight_colombia() -> None:
    # Friday 23:30 Colombia (Saturday 04:30 UTC): the cut has not happened yet.
    assert semana_fin_de(datetime(2026, 11, 14, 4, 30, tzinfo=UTC)) == F0
    # Saturday 00:05 Colombia (05:05 UTC): the week of Friday the 13th is closed.
    assert semana_fin_de(datetime(2026, 11, 14, 5, 5, tzinfo=UTC)) == F1
    assert semana_fin_de(datetime(2026, 11, 18, 12, tzinfo=UTC)) == F1
    assert momento_corte(F1) == datetime(2026, 11, 14, 5, tzinfo=UTC)


def test_first_close_is_only_a_baseline(uow: SqlAlchemyUnitOfWork) -> None:
    _video(uow, "a")
    _corte(uow, F1, a=1000)

    assert generar_edicion(uow, F1) is None


def test_ranks_by_exact_difference_between_closes(uow: SqlAlchemyUnitOfWork) -> None:
    for v in ("a", "b"):
        _video(uow, v)
    _corte(uow, F0, a=1_000_000, b=1_000)
    _corte(uow, F1, a=1_010_000, b=51_000)

    ed = generar_edicion(uow, F1)

    assert ed is not None
    assert [f.video_id for f in ed.filas] == ["b", "a"]
    assert ed.filas[0].vistas_semana == 50_000 and ed.filas[0].vistas_totales == 51_000


def test_new_video_counts_from_zero_and_old_ones_without_base_are_left_out(
    uow: SqlAlchemyUnitOfWork,
) -> None:
    _video(uow, "base")
    _video(uow, "nuevo", publicado=momento_corte(F0).astimezone(UTC) + timedelta(days=2))
    _video(uow, "viejo")  # old, but first seen this week: no exact base
    _corte(uow, F0, base=10)
    _corte(uow, F1, base=20, nuevo=700, viejo=9_999_999)

    ed = generar_edicion(uow, F1)

    assert ed is not None
    assert [f.video_id for f in ed.filas] == ["nuevo", "base"]
    assert ed.filas[0].vistas_semana == 700
    assert ed.sin_base == 1


def test_excluded_shorts_and_pins_are_respected(uow: SqlAlchemyUnitOfWork) -> None:
    _video(uow, "a")
    _video(uow, "excl", excluido=True)
    _video(uow, "corto", duracion_segundos=45)
    _video(uow, "fijo", fijado_posicion=1)
    _corte(uow, F0, a=0, excl=0, corto=0, fijo=0)
    _corte(uow, F1, a=900, excl=9_000, corto=8_000, fijo=5)

    ed = generar_edicion(uow, F1)

    assert ed is not None
    assert [f.video_id for f in ed.filas] == ["fijo", "a"]
    assert ed.filas[0].fijado is True


def test_trend_compares_with_the_previous_published_edition(uow: SqlAlchemyUnitOfWork) -> None:
    for v in ("a", "b", "n"):
        _video(uow, v)
    _corte(uow, F0, a=0, b=0)
    _corte(uow, F1, a=900, b=800)
    generar_edicion(uow, F1)
    publicar_edicion(uow, F1)  # a is #1, b is #2
    _corte(uow, F2, a=1000, b=2800, n=50)
    uow.chart.save_video(
        VideoChart(
            video_id="n",
            canal_id="UCx",
            titulo="Tema n",
            publicado_en=momento_corte(F1).astimezone(UTC) + timedelta(hours=1),
        )
    )

    ed = generar_edicion(uow, F2)

    assert ed is not None
    por_id = {f.video_id: f for f in ed.filas}
    assert por_id["b"].tendencia == "sube" and por_id["b"].posicion_anterior == 2
    assert por_id["a"].tendencia == "baja"
    assert por_id["n"].tendencia == "nuevo"


def test_trend_is_unknown_without_a_published_edition(uow: SqlAlchemyUnitOfWork) -> None:
    _video(uow, "a")
    _corte(uow, F0, a=0)
    _corte(uow, F1, a=10)

    ed = generar_edicion(uow, F1)

    assert ed is not None and ed.filas[0].tendencia is None


def test_a_published_edition_cannot_be_regenerated(uow: SqlAlchemyUnitOfWork) -> None:
    _video(uow, "a")
    _corte(uow, F0, a=0)
    _corte(uow, F1, a=10)
    generar_edicion(uow, F1)
    publicar_edicion(uow, F1)

    with pytest.raises(EdicionPublicadaError):
        generar_edicion(uow, F1)
    guardada = uow.chart.get_edicion(F1)
    assert guardada is not None and guardada.estado == ESTADO_PUBLICADA


def test_regenerating_a_draft_replaces_its_rows(uow: SqlAlchemyUnitOfWork) -> None:
    for v in ("a", "b"):
        _video(uow, v)
    _corte(uow, F0, a=0, b=0)
    _corte(uow, F1, a=100, b=50)
    primera = generar_edicion(uow, F1)
    assert primera is not None and len(primera.filas) == 2
    _video(uow, "a", excluido=True)

    segunda = generar_edicion(uow, F1)

    assert segunda is not None and [f.video_id for f in segunda.filas] == ["b"]
    guardada = uow.chart.get_edicion(F1)
    assert guardada is not None and [f.video_id for f in guardada.filas] == ["b"]


class _Lector(FakeYouTubeReader):
    def __init__(self, vistas: int, **kw: object) -> None:
        super().__init__(**kw)  # type: ignore[arg-type]
        self._vistas = vistas

    def catalogo_canal(self, canal_id: str, *, maximo: int = 500) -> list[VideoYouTube]:
        if canal_id == self._canal_con_error:
            raise YouTubeError("canal de prueba con error")
        return [
            VideoYouTube(
                video_id="v1v1v1v1v1v", canal_id=canal_id, titulo="Tema", publicado_en=VIEJO
            )
        ]

    def detalles(self, video_ids: list[str]) -> dict[str, DetalleVideo]:
        return {v: DetalleVideo(vistas=self._vistas, duracion_segundos=200) for v in video_ids}


def test_close_discovers_measures_and_builds_the_draft(uow: SqlAlchemyUnitOfWork) -> None:
    uow.chart.save_canal(CanalChart(canal_id=CANAL, nombre="Canal"))
    primero = cerrar_semana(uow, _Lector(100), datetime(2026, 11, 14, 5, 5, tzinfo=UTC))
    segundo = cerrar_semana(uow, _Lector(450), datetime(2026, 11, 21, 5, 5, tzinfo=UTC))

    assert primero.edicion_generada is False and primero.nota
    assert segundo.edicion_generada is True and not segundo.hubo_errores
    guardada = uow.chart.get_edicion(F2)
    assert guardada is not None and guardada.filas[0].vistas_semana == 350


def test_close_with_a_statistics_failure_builds_no_edition(uow: SqlAlchemyUnitOfWork) -> None:
    uow.chart.save_canal(CanalChart(canal_id=CANAL, nombre="Canal"))
    cerrar_semana(uow, _Lector(100), datetime(2026, 11, 14, 5, 5, tzinfo=UTC))

    class Roto(_Lector):
        def detalles(self, video_ids: list[str]) -> dict[str, DetalleVideo]:
            raise YouTubeError("cuota")

    res = cerrar_semana(uow, Roto(0), datetime(2026, 11, 21, 5, 5, tzinfo=UTC))

    assert res.hubo_errores and res.error_estadisticas == "cuota"
    assert uow.chart.get_edicion(F2) is None


def test_close_reports_a_failing_channel_but_keeps_going(uow: SqlAlchemyUnitOfWork) -> None:
    malo = "UC" + "b" * 22
    uow.chart.save_canal(CanalChart(canal_id=malo, nombre="Malo"))
    uow.chart.save_canal(CanalChart(canal_id=CANAL, nombre="Bueno"))

    res = cerrar_semana(
        uow, _Lector(10, canal_con_error=malo), datetime(2026, 11, 14, 5, 5, tzinfo=UTC)
    )

    assert res.canales_ok == 1 and len(res.canales_con_error) == 1 and res.hubo_errores


def test_retention_purges_statistics_older_than_the_limit(uow: SqlAlchemyUnitOfWork) -> None:
    from core.entities.chart import SnapshotVistas
    from core.services.chart_service import purgar_datos_antiguos

    hoy = date(2026, 12, 20)
    _video(uow, "a")
    # Old (45 days) and recent (5 days) data of every kind.
    uow.chart.save_snapshot(SnapshotVistas("a", hoy - timedelta(days=45), 10))
    uow.chart.save_snapshot(SnapshotVistas("a", hoy - timedelta(days=5), 20))
    viejo, reciente = hoy - timedelta(days=45), hoy - timedelta(days=5)
    for semana, total in ((viejo - timedelta(days=7), 1), (viejo, 2), (reciente, 3)):
        _corte(uow, semana, a=total)
    _corte(uow, reciente - timedelta(days=7), a=1)
    generar_edicion(uow, viejo)
    generar_edicion(uow, reciente)

    res = purgar_datos_antiguos(uow, hoy, 30)

    assert (res.snapshots, res.cortes, res.ediciones) == (1, 2, 1)
    assert [s.fecha for s in uow.chart.list_snapshots(["a"], desde=date(2020, 1, 1))["a"]] == [
        hoy - timedelta(days=5)
    ]
    assert uow.chart.get_edicion(viejo) is None
    assert uow.chart.get_edicion(reciente) is not None
    assert uow.chart.list_cortes(reciente) == {"a": 3}


def test_retention_can_be_raised_after_approval_and_is_idempotent(
    uow: SqlAlchemyUnitOfWork,
) -> None:
    from core.entities.chart import SnapshotVistas
    from core.services.chart_service import purgar_datos_antiguos

    hoy = date(2026, 12, 20)
    _video(uow, "a")
    uow.chart.save_snapshot(SnapshotVistas("a", hoy - timedelta(days=200), 5))

    assert purgar_datos_antiguos(uow, hoy, 1095).snapshots == 0
    assert purgar_datos_antiguos(uow, hoy, 30).snapshots == 1
    assert purgar_datos_antiguos(uow, hoy, 30).snapshots == 0
    with pytest.raises(ValueError):
        purgar_datos_antiguos(uow, hoy, 0)


def test_weekly_status_tells_what_the_editor_must_do(uow: SqlAlchemyUnitOfWork) -> None:
    from core.services.chart_semanal_service import estado_semanal

    sabado_temprano = datetime(2026, 11, 14, 5, 30, tzinfo=UTC)  # 30 min after the cut
    sabado_tarde = datetime(2026, 11, 14, 9, 0, tzinfo=UTC)
    _video(uow, "a")

    assert estado_semanal(uow, sabado_temprano).nivel == "info"  # cron still has time
    assert estado_semanal(uow, sabado_tarde).nivel == "error"  # close never ran

    _corte(uow, F1, a=100)
    assert estado_semanal(uow, sabado_tarde).nivel == "info"  # baseline only

    _corte(uow, F0, a=10)
    assert estado_semanal(uow, sabado_tarde).nivel == "error"  # closed, no edition

    generar_edicion(uow, F1)
    estado = estado_semanal(uow, sabado_tarde)
    assert estado.nivel == "atencion" and "borrador" in estado.mensaje

    publicar_edicion(uow, F1)
    assert estado_semanal(uow, sabado_tarde).nivel == "ok"
