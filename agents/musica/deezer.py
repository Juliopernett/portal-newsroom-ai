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

    def pistas(self, consulta: str, limite: int = 10) -> list[dict]:
        """Raw search for the editor's picker: id, title, artist, rank and link per track."""
        try:
            r = requests.get(
                _API, params={"q": consulta, "limit": limite}, timeout=_TIMEOUT_SECONDS
            )
            r.raise_for_status()
            datos = r.json().get("data") or []
        except (requests.RequestException, ValueError):
            return []
        return [
            {
                "id": str(i["id"]),
                "titulo": str(i.get("title", "")),
                "artista": str(i.get("artist", {}).get("name", "")),
                "rank": int(i.get("rank") or 0),
                "url": str(i.get("link", "")),
            }
            for i in datos
            if i.get("id")
        ]

    def por_id(self, track_id: str) -> ApoyoCancion | None:
        """The figure of a track the editor picked by hand."""
        try:
            r = requests.get(f"https://api.deezer.com/track/{track_id}", timeout=_TIMEOUT_SECONDS)
            r.raise_for_status()
            item = r.json()
        except (requests.RequestException, ValueError):
            return None
        if not item.get("id"):
            return None
        return ApoyoCancion(
            plataforma=self.plataforma,
            valor=int(item.get("rank") or 0),
            url=str(item.get("link", "")),
        )
