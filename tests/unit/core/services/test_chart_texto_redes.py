from datetime import date

from core.entities.chart import FilaEdicion
from core.services.chart_texto_redes import URL_RADAR, texto_redes


def _fila(pos, titulo, artista, tendencia=None, anterior=None):
    return FilaEdicion(
        posicion=pos,
        video_id=str(pos),
        titulo=titulo,
        artista=artista,
        url="u",
        vistas_semana=1,
        vistas_totales=2,
        tendencia=tendencia,
        posicion_anterior=anterior,
    )


def test_texto_incluye_primero_enlace_y_movimientos():
    texto = texto_redes(
        [_fila(2, "B", "Silvestre Dangond", "sube", 5), _fila(1, "A", "Carlos Vives", "igual", 1)],
        date(2026, 11, 20),
    )
    assert "del 14 al 20 de noviembre" in texto
    assert "«A» de Carlos Vives" in texto
    assert "del puesto 5 al 2" in texto
    assert URL_RADAR in texto
    assert "#CarlosVives" in texto


def test_rango_cruza_de_mes_y_sin_filas():
    assert "del 28 de octubre al 3 de noviembre" in texto_redes(
        [_fila(1, "A", None)], date(2026, 11, 3)
    )
    assert texto_redes([], date(2026, 11, 3)) == ""
