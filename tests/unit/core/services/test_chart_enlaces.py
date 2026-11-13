"""Unit tests: linking chart rows to artist pages."""

from __future__ import annotations

import requests

from agents.portal.catalogo_artistas import CatalogoArtistas, parsear_catalogo
from core.services.chart_enlaces import pagina_del_artista

CATALOGO = {
    "oscar gamarra": "https://portalvallenato.com/oscar-gamarra/",
    "la china laura hamburger": "https://portalvallenato.com/laura-hamburger-la-china/",
    "kaleth morales": "https://portalvallenato.com/kaleth-morales/",
    "kaleth ramirez": "https://portalvallenato.com/kaleth-ramirez/",
}


def test_exact_match_ignores_accents_and_case() -> None:
    assert (
        pagina_del_artista("Óscar Gamarra", CATALOGO)
        == "https://portalvallenato.com/oscar-gamarra/"
    )


def test_a_name_inside_a_multi_name_entry_matches() -> None:
    assert pagina_del_artista("La China", CATALOGO).endswith("laura-hamburger-la-china/")  # type: ignore[union-attr]


def test_an_ambiguous_name_is_not_guessed() -> None:
    assert pagina_del_artista("Kaleth", CATALOGO) is None


def test_no_page_or_no_artist_gives_no_link() -> None:
    assert pagina_del_artista("Desconocido", CATALOGO) is None
    assert pagina_del_artista(None, CATALOGO) is None
    assert pagina_del_artista("   ", CATALOGO) is None


def test_the_grid_is_parsed() -> None:
    contenido = (
        '<ul class="pv-art">\n<li data-n="oscar gamarra" data-notas="3"><a href="https://portalvallenato.com/oscar-gamarra/">'
        '<img src="x"></a></li>\n<li data-n="ana del castillo" data-notas="2">'
        '<a href="https://portalvallenato.com/ana-del-castillo-cantante/"></a></li></ul>'
    )

    assert parsear_catalogo(contenido) == {
        "oscar gamarra": "https://portalvallenato.com/oscar-gamarra/",
        "ana del castillo": "https://portalvallenato.com/ana-del-castillo-cantante/",
    }


def test_the_catalogue_is_cached_and_survives_a_website_failure() -> None:
    reloj = [0.0]
    llamadas = {"n": 0}
    caer = {"si": False}

    def descargar() -> str:
        llamadas["n"] += 1
        if caer["si"]:
            raise requests.ConnectionError("caído")
        return '<li data-n="a b" data-notas="1"><a href="https://portalvallenato.com/a-b/">'

    cat = CatalogoArtistas(descargar, ahora=lambda: reloj[0])

    assert cat.obtener() == {"a b": "https://portalvallenato.com/a-b/"}
    cat.obtener()
    assert llamadas["n"] == 1  # cached
    reloj[0] = 7 * 3600
    caer["si"] = True
    assert cat.obtener() == {"a b": "https://portalvallenato.com/a-b/"}  # last good copy
