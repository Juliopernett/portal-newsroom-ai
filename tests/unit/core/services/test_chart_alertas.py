from datetime import date, timedelta

from core.entities.chart import SnapshotVistas
from core.services.chart_alertas import evaluar_reacciones

FIN = date(2026, 11, 27)


def _snaps(vistas, me_gusta, comentarios=None, *, antes=None):
    """Latest snapshot plus an optional one 7 days earlier: (views, likes, comments)."""
    lista = []
    if antes:
        lista.append(SnapshotVistas("x", FIN - timedelta(days=7), *antes))
    lista.append(SnapshotVistas("x", FIN, vistas, me_gusta, comentarios))
    return lista


def _normales(n=5):
    return {f"ok{i}": _snaps(1_000_000, 20_000 + i * 500, 1_500) for i in range(n)}


def test_flags_a_song_with_far_fewer_likes_than_the_rest() -> None:
    canciones = {**_normales(), "raro": _snaps(5_500_000, 8_100, 1_500)}
    alertas = evaluar_reacciones(canciones, FIN)
    assert set(alertas) == {"raro"}
    assert alertas["raro"].base == "total"
    assert alertas["raro"].me_gusta_pct == 0.147
    assert "0,15 %" in alertas["raro"].motivo


def test_uses_the_week_when_there_is_a_week_of_history() -> None:
    # +1M views this week but only +120 likes, though its lifetime ratio looks fine.
    raro = _snaps(5_500_000, 100_120, 9_000, antes=(4_500_000, 100_000, 8_900))
    canciones = {**_normales(), "raro": raro}
    alertas = evaluar_reacciones(canciones, FIN)
    assert alertas["raro"].base == "semana"
    assert alertas["raro"].me_gusta_pct == 0.012


def test_normal_songs_are_not_flagged() -> None:
    assert evaluar_reacciones(_normales(), FIN) == {}


def test_needs_enough_songs_for_a_median() -> None:
    canciones = {**_normales(2), "raro": _snaps(5_500_000, 8_100, 1_500)}
    assert evaluar_reacciones(canciones, FIN) == {}


def test_songs_without_reaction_data_are_ignored() -> None:
    canciones = {**_normales(), "oculto": [SnapshotVistas("x", FIN, 5_000_000)]}
    assert evaluar_reacciones(canciones, FIN) == {}


def test_low_comments_alone_also_flag() -> None:
    canciones = {**_normales(), "mudo": _snaps(1_000_000, 21_000, 20)}
    assert set(evaluar_reacciones(canciones, FIN)) == {"mudo"}
