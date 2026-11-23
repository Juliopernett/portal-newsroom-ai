"""Match a chart row to the same song on Spotify/Deezer (pure logic, no network).

Searching a platform returns fuzzy results, so a hit only counts when the artist
and the title both agree after cleaning YouTube's decorations ("Video Oficial",
"(Letra)", "Artist - " prefixes...). A wrong link is worse than no link.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from core.services.chart_enlaces import normalizar_nombre

_ENTRE_PARENTESIS = re.compile(r"[\(\[\{][^\)\]\}]*[\)\]\}]")
_RUIDO = re.compile(
    r"\b(video oficial|official video|official audio|audio oficial|video lyric|lyric video|"
    r"letra|lyrics|video|oficial|hd|4k)\b",
    re.IGNORECASE,
)


def limpiar_titulo(titulo: str, artista: str | None = None) -> str:
    """The song name without the YouTube decorations (brackets, 'Video Oficial', 'Artist - ')."""
    t = _ENTRE_PARENTESIS.sub(" ", titulo)
    t = _RUIDO.sub(" ", t)
    partes = re.split(r"\s[-–—|]\s", t)
    if artista and len(partes) == 2:
        # "Artist(s) - Song" or "Song - Artist": drop the side that names the artist.
        na = normalizar_nombre(artista)
        izq, der = normalizar_nombre(partes[0]), normalizar_nombre(partes[1])
        if na and na in izq:
            t = partes[1]
        elif na and na in der:
            t = partes[0]
    elif artista is None and len(partes) == 2:
        t = partes[1]
    return re.sub(r"\s+", " ", t).strip(" -–—|:")


def coincide(artista: str, titulo: str, artista_hallado: str, titulo_hallado: str) -> bool:
    """Whether a search result is the same song (artist and title both agree)."""
    a, ah = normalizar_nombre(artista), normalizar_nombre(artista_hallado)
    t, th = normalizar_nombre(titulo), normalizar_nombre(titulo_hallado)
    if not (a and ah and t and th):
        return False
    if not (a in ah or ah in a):
        return False
    return t == th or (len(t) >= 4 and (t in th or th in t))


def buscar_apoyo(
    canciones: list[tuple[str, str | None, str]],
    buscadores: list,
    cache: dict,
    *,
    ahora: float,
    ttl_segundos: float = 6 * 3600,
) -> dict[str, dict[str, tuple[int, str]]]:
    """For each (video_id, artist, title) the figure/link per platform; missing = no match.

    Looks every song up on every platform in parallel and remembers the answers (also
    the misses) for `ttl_segundos` in `cache`, so reopening the panel costs nothing.
    """
    pendientes = []
    for video_id, artista, titulo in canciones:
        if not artista:
            continue
        for b in buscadores:
            clave = (b.plataforma, normalizar_nombre(artista), normalizar_nombre(titulo))
            hit = cache.get(clave)
            if hit is None or ahora - hit[0] > ttl_segundos:
                pendientes.append((video_id, artista, titulo, b, clave))

    def _buscar(p: tuple) -> object:
        _, artista, titulo, b, _clave = p
        try:
            return b.buscar(artista, titulo)
        except Exception:  # noqa: BLE001 - a failing platform must not break the panel
            return False  # not cached: try again next time

    with ThreadPoolExecutor(max_workers=6) as pool:
        for p, r in zip(pendientes, pool.map(_buscar, pendientes), strict=True):
            if r is not False:
                cache[p[4]] = (ahora, r)

    salida: dict[str, dict[str, tuple[int, str]]] = {}
    for video_id, artista, titulo in canciones:
        if not artista:
            continue
        for b in buscadores:
            hit = cache.get((b.plataforma, normalizar_nombre(artista), normalizar_nombre(titulo)))
            if hit and hit[1]:
                salida.setdefault(video_id, {})[b.plataforma] = (hit[1].valor, hit[1].url)
    return salida
