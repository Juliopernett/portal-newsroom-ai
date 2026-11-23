"""Spotify Web API adapter (client-credentials): the song's popularity (0-100) and link.

Needs `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` (a free app at developer.spotify.com).
Error messages never include credentials.
"""

from __future__ import annotations

import time

import requests

from core.ports.musica_apoyo import ApoyoCancion
from core.services.chart_apoyo import coincide, limpiar_titulo

_TOKEN = "https://accounts.spotify.com/api/token"  # noqa: S105 - URL, not a secret
_SEARCH = "https://api.spotify.com/v1/search"
_TIMEOUT_SECONDS = 10


class SpotifyBuscador:
    plataforma = "spotify"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._auth = (client_id, client_secret)
        self._token: str | None = None
        self._vence = 0.0

    def _bearer(self) -> str | None:
        if self._token and time.monotonic() < self._vence:
            return self._token
        try:
            r = requests.post(
                _TOKEN,
                data={"grant_type": "client_credentials"},
                auth=self._auth,
                timeout=_TIMEOUT_SECONDS,
            )
            r.raise_for_status()
            j = r.json()
        except (requests.RequestException, ValueError):
            return None
        self._token = str(j["access_token"])
        self._vence = time.monotonic() + int(j.get("expires_in", 3600)) - 60
        return self._token

    def buscar(self, artista: str, titulo: str) -> ApoyoCancion | None:
        limpio = limpiar_titulo(titulo, artista)
        token = self._bearer()
        if not limpio or not token:
            return None
        try:
            r = requests.get(
                _SEARCH,
                params={
                    "q": f"track:{limpio} artist:{artista}",
                    "type": "track",
                    "limit": 5,
                    "market": "CO",
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=_TIMEOUT_SECONDS,
            )
            r.raise_for_status()
            items = (r.json().get("tracks") or {}).get("items") or []
        except (requests.RequestException, ValueError):
            return None
        for item in items:
            nombres = " ".join(a.get("name", "") for a in item.get("artists", []))
            if coincide(artista, limpio, nombres, item.get("name", "")):
                return ApoyoCancion(
                    plataforma=self.plataforma,
                    valor=int(item.get("popularity") or 0),
                    url=str(item["external_urls"]["spotify"]),
                )
        return None
