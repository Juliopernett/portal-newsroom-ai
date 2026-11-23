"""Deezer public API adapter (no key needed): the song's `rank` and its link."""

from __future__ import annotations

import requests

from core.ports.musica_apoyo import ApoyoCancion
from core.services.chart_apoyo import coincide, limpiar_titulo

_API = "https://api.deezer.com/search"
_TIMEOUT_SECONDS = 10


class DeezerBuscador:
    plataforma = "deezer"

    def buscar(self, artista: str, titulo: str) -> ApoyoCancion | None:
        limpio = limpiar_titulo(titulo, artista)
        if not limpio:
            return None
        try:
            r = requests.get(
                _API,
                params={"q": f"{artista} {limpio}", "limit": 8},
                timeout=_TIMEOUT_SECONDS,
            )
            r.raise_for_status()
            datos = r.json().get("data") or []
        except (requests.RequestException, ValueError):
            return None
        for item in datos:
            if coincide(
                artista, limpio, item.get("artist", {}).get("name", ""), item.get("title", "")
            ):
                return ApoyoCancion(
                    plataforma=self.plataforma,
                    valor=int(item.get("rank") or 0),
                    url=str(item["link"]),
                )
        return None
