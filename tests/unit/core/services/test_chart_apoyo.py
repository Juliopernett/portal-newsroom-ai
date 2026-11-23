from core.ports.musica_apoyo import ApoyoCancion
from core.services.chart_apoyo import buscar_apoyo, coincide, limpiar_titulo


def test_limpiar_titulo_quita_decoraciones_y_prefijo_de_artista():
    assert (
        limpiar_titulo("Silvestre Dangond - La Gota Fría (Video Oficial)", "Silvestre Dangond")
        == "La Gota Fría"
    )
    assert limpiar_titulo("Canción X [Letra] | Official Video", "Fulano") == "Canción X"


def test_coincide_exige_artista_y_titulo():
    assert coincide("Silvestre Dangond", "La Gota Fria", "Silvestre Dangond", "La Gota Fría")
    assert not coincide("Silvestre Dangond", "La Gota Fria", "Otro Artista", "La Gota Fría")
    assert not coincide("Silvestre Dangond", "La Gota Fria", "Silvestre Dangond", "Otra Cosa")


class _Falso:
    plataforma = "deezer"

    def __init__(self):
        self.llamadas = 0

    def buscar(self, artista, titulo):
        self.llamadas += 1
        return ApoyoCancion(plataforma="deezer", valor=500, url="u") if titulo == "A" else None


def test_buscar_apoyo_usa_cache_y_omite_sin_coincidencia():
    b, cache = _Falso(), {}
    canciones = [("v1", "Artista", "A"), ("v2", "Artista", "B"), ("v3", None, "A")]
    assert buscar_apoyo(canciones, [b], cache, ahora=1000.0) == {"v1": {"deezer": (500, "u")}}
    buscar_apoyo(canciones, [b], cache, ahora=1001.0)
    assert b.llamadas == 2  # the second call came from the cache
