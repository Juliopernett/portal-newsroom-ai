"""Unit tests for core.services.chart_service.calcular_chart."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from core.entities.chart import SnapshotVistas, VideoChart
from core.services.chart_service import Tendencia, calcular_chart

HOY = date(2026, 11, 10)


def _video(vid: str, **kw: object) -> VideoChart:
    return VideoChart(
        video_id=vid,
        canal_id="UCx",
        titulo=f"Tema {vid}",
        publicado_en=datetime(2026, 10, 1, tzinfo=UTC),
        **kw,  # type: ignore[arg-type]
    )


def _snaps(vid: str, hace: dict[int, int]) -> list[SnapshotVistas]:
    """`hace` maps days-ago → total views on that day."""
    return [SnapshotVistas(vid, HOY - timedelta(days=d), v) for d, v in hace.items()]


def test_ranks_by_views_gained_in_the_week_not_by_total() -> None:
    videos = [_video("a"), _video("b")]
    snaps = {
        "a": _snaps("a", {7: 1_000_000, 0: 1_010_000}),  # huge total, +10k
        "b": _snaps("b", {7: 1_000, 0: 51_000}),  # small total, +50k
    }

    chart = calcular_chart(videos, snaps, HOY)

    assert [p.video.video_id for p in chart] == ["b", "a"]
    assert chart[0].vistas_semana == 50_000 and chart[0].vistas_totales == 51_000


def test_video_with_less_than_three_days_of_history_is_not_ranked() -> None:
    chart = calcular_chart([_video("a")], {"a": _snaps("a", {1: 100, 0: 900})}, HOY)

    assert chart == []


def test_partial_history_is_scaled_to_a_week_and_flagged() -> None:
    chart = calcular_chart([_video("a")], {"a": _snaps("a", {4: 1_000, 0: 5_000})}, HOY)

    assert chart[0].parcial is True
    assert chart[0].vistas_semana == round(4_000 * 7 / 4)


def test_stale_video_without_a_recent_snapshot_is_dropped() -> None:
    chart = calcular_chart([_video("a")], {"a": _snaps("a", {12: 100, 8: 900})}, HOY)

    assert chart == []


def test_excluded_videos_never_appear() -> None:
    videos = [_video("a", excluido=True), _video("b")]
    snaps = {v: _snaps(v, {7: 0, 0: 5_000}) for v in ("a", "b")}

    assert [p.video.video_id for p in calcular_chart(videos, snaps, HOY)] == ["b"]


def test_pinned_video_is_forced_to_its_position_and_others_shift() -> None:
    videos = [_video("a"), _video("b"), _video("c", fijado_posicion=1)]
    snaps = {
        "a": _snaps("a", {7: 0, 0: 9_000}),
        "b": _snaps("b", {7: 0, 0: 8_000}),
        "c": _snaps("c", {7: 0, 0: 10}),
    }

    chart = calcular_chart(videos, snaps, HOY)

    assert [p.video.video_id for p in chart] == ["c", "a", "b"]
    assert chart[0].fijado is True and chart[1].fijado is False


def test_pinned_video_without_data_still_shows_with_zero_views() -> None:
    chart = calcular_chart([_video("c", fijado_posicion=1)], {}, HOY)

    assert chart[0].vistas_semana == 0 and chart[0].fijado is True


def test_top_is_capped() -> None:
    videos = [_video(str(i)) for i in range(15)]
    snaps = {str(i): _snaps(str(i), {7: 0, 0: 1000 + i}) for i in range(15)}

    assert len(calcular_chart(videos, snaps, HOY, top=10)) == 10


def test_trend_without_any_earlier_ranking_is_unknown_not_new() -> None:
    chart = calcular_chart([_video("a")], {"a": _snaps("a", {7: 0, 0: 5_000})}, HOY)

    assert chart[0].tendencia is None


def test_trend_compares_with_the_ranking_a_week_earlier() -> None:
    videos = [_video("a"), _video("b"), _video("n")]
    snaps = {
        # a: first a week ago, second now.   b: second a week ago, first now.
        "a": _snaps("a", {14: 0, 7: 9_000, 0: 9_500}),
        "b": _snaps("b", {14: 0, 7: 5_000, 0: 20_000}),
        # n did not exist last week.
        "n": _snaps("n", {7: 0, 0: 400}),
    }

    chart = {p.video.video_id: p for p in calcular_chart(videos, snaps, HOY)}

    assert chart["b"].tendencia is Tendencia.SUBE and chart["b"].posicion_anterior == 2
    assert chart["a"].tendencia is Tendencia.BAJA
    assert chart["n"].tendencia is Tendencia.NUEVO and chart["n"].posicion_anterior is None


def test_shorts_are_kept_out_of_the_chart_by_length_or_hashtag() -> None:
    videos = [
        _video("cancion", duracion_segundos=215),
        _video("corto", duracion_segundos=45),
        VideoChart(
            video_id="tag",
            canal_id="UCx",
            titulo="Adelanto #Shorts",
            publicado_en=datetime(2026, 10, 1, tzinfo=UTC),
            duracion_segundos=200,
        ),
    ]
    snaps = {v.video_id: _snaps(v.video_id, {7: 0, 0: 9_000}) for v in videos}

    assert [p.video.video_id for p in calcular_chart(videos, snaps, HOY)] == ["cancion"]


def test_unknown_duration_is_not_treated_as_a_short() -> None:
    video = _video("a")  # duracion_segundos=None until the next collection

    assert video.es_short is False
    chart = calcular_chart([video], {"a": _snaps("a", {7: 0, 0: 5_000})}, HOY)
    assert len(chart) == 1


def test_an_explicit_pin_overrides_the_short_filter() -> None:
    video = _video("a", duracion_segundos=30, fijado_posicion=1)

    chart = calcular_chart([video], {}, HOY)

    assert [p.video.video_id for p in chart] == ["a"] and chart[0].fijado is True


def test_clips_titled_only_with_a_date_or_emojis_are_not_songs() -> None:
    def titulo(t: str) -> VideoChart:
        return VideoChart(
            video_id="x",
            canal_id="UCx",
            titulo=t,
            publicado_en=datetime(2026, 10, 1, tzinfo=UTC),
            duracion_segundos=200,
        )

    for sin_nombre in ("6 de noviembre de 2026", "🎶🪗", "❤️🙏🏻", "2026"):
        assert titulo(sin_nombre).es_short is True, sin_nombre
    for cancion in (
        "La Playita",
        "20 de julio",
        "31 de octubre",
        "De noviembre a diciembre",
        "Adelanto de mi canción",
    ):
        assert titulo(cancion).es_short is False, cancion


def test_length_limit_is_90_seconds_inclusive() -> None:
    assert _video("a", duracion_segundos=90).es_short is True
    assert _video("b", duracion_segundos=91).es_short is False


def _con(
    vid: str, titulo: str, artista: str | None, canal: str = "UCx", **kw: object
) -> VideoChart:
    return VideoChart(
        video_id=vid,
        canal_id=canal,
        titulo=titulo,
        artista=artista,
        publicado_en=datetime(2026, 10, 1, tzinfo=UTC),
        **kw,  # type: ignore[arg-type]
    )


def test_the_same_song_uploaded_twice_takes_one_place_the_most_viewed_one() -> None:
    videos = [
        _con("oficial", "La Playita (Video Oficial)", "Silvestre", "UC1"),
        _con("vevo", "LA PLAYITA [Official Video] #vallenato", "Silvestre", "UC2"),
        _con("otra", "Otra Canción", "Silvestre", "UC1"),
    ]
    snaps = {
        "oficial": _snaps("oficial", {7: 0, 0: 9_000}),
        "vevo": _snaps("vevo", {7: 0, 0: 12_000}),
        "otra": _snaps("otra", {7: 0, 0: 5_000}),
    }

    chart = calcular_chart(videos, snaps, HOY)

    assert [p.video.video_id for p in chart] == ["vevo", "otra"]


def test_decorations_are_ignored_when_matching_a_song() -> None:
    a = _con("a", "La Playita (Video Oficial) #vallenato", "Silvestre")
    b = _con("b", "La  Playita [Official Audio]", "silvestre")
    c = _con("c", "La Playita (En Vivo)", "Silvestre")  # a different recording

    from core.services.chart_service import clave_cancion

    assert clave_cancion(a) == clave_cancion(b)
    assert clave_cancion(a) != clave_cancion(c)


def test_two_songs_with_the_same_title_from_unknown_artists_never_merge() -> None:
    from core.services.chart_service import clave_cancion

    assert clave_cancion(_con("a", "El Camino", None, "UC1")) != clave_cancion(
        _con("b", "El Camino", None, "UC2")
    )


def test_a_pinned_duplicate_claims_the_song_over_a_more_viewed_copy() -> None:
    videos = [
        _con("fijo", "La Playita", "Silvestre", "UC1", fijado_posicion=1),
        _con("mas_vistas", "La Playita (Video Oficial)", "Silvestre", "UC2"),
    ]
    snaps = {
        "fijo": _snaps("fijo", {7: 0, 0: 10}),
        "mas_vistas": _snaps("mas_vistas", {7: 0, 0: 90_000}),
    }

    assert [p.video.video_id for p in calcular_chart(videos, snaps, HOY)] == ["fijo"]
