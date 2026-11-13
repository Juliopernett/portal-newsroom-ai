"""Links from the public chart rows to the artist's page on the website.

Pure logic: the catalogue (normalized artist name -> page URL) comes from the
website, see `agents.portal.catalogo_artistas`.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping


def normalizar_nombre(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9ñ]+", " ", sin_tildes).strip()


def pagina_del_artista(artista: str | None, catalogo: Mapping[str, str]) -> str | None:
    """The artist's page URL, or None when the website has no page for them.

    Exact match on the normalized name first. Otherwise the name has to appear
    as whole words inside exactly one catalogue entry (for example "la china"
    inside "la china laura hamburger"); if it fits several, no link is made
    rather than guessing.
    """
    if not artista:
        return None
    nombre = normalizar_nombre(artista)
    if not nombre:
        return None
    if nombre in catalogo:
        return catalogo[nombre]
    patron = re.compile(rf"(^| ){re.escape(nombre)}( |$)")
    coincidencias = {url for clave, url in catalogo.items() if patron.search(clave)}
    return coincidencias.pop() if len(coincidencias) == 1 else None
