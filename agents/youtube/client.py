"""Real YouTube Data API v3 adapter for `core.ports.youtube_reader.YouTubeReader`.

Error messages never include the request URL: it carries the API key as a
query parameter, and `requests` puts the URL in its exception text.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import requests

from config.settings import Settings
from core.ports.youtube_reader import CanalResuelto, VideoYouTube, YouTubeError

_API = "https://www.googleapis.com/youtube/v3"
_TIMEOUT_SECONDS = 20
_INTENTOS = 2
_ID_CANAL = re.compile(r"^UC[\w-]{22}$")
_ID_VIDEO = re.compile(r"^[\w-]{11}$")


class YouTubeConfigurationError(RuntimeError):
    """`YOUTUBE_API_KEY` is not set."""


def _fecha(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00")).astimezone(UTC)


def _miniatura(snippet: dict[str, Any]) -> str | None:
    miniaturas = snippet.get("thumbnails") or {}
    for tamano in ("medium", "high", "default", "standard"):
        if tamano in miniaturas:
            url = miniaturas[tamano].get("url")
            return str(url) if url else None
    return None


def _id_de_video(referencia: str) -> str:
    ref = referencia.strip()
    if _ID_VIDEO.match(ref):
        return ref
    for patron in (
        r"[?&]v=([\w-]{11})",
        r"youtu\.be/([\w-]{11})",
        r"/shorts/([\w-]{11})",
        r"/embed/([\w-]{11})",
    ):
        m = re.search(patron, ref)
        if m:
            return m.group(1)
    raise YouTubeError("No pude reconocer el video en esa dirección.")


class YouTubeDataApiReader:
    """`YouTubeReader` against the real YouTube Data API v3."""

    def __init__(self, settings: Settings) -> None:
        if not settings.youtube_api_key:
            raise YouTubeConfigurationError("YOUTUBE_API_KEY no está configurada en Railway.")
        self._key = settings.youtube_api_key

    def _get(self, ruta: str, **params: str | int) -> dict[str, Any]:
        params["key"] = self._key
        for intento in range(_INTENTOS):
            ultimo = intento == _INTENTOS - 1
            try:
                respuesta = requests.get(f"{_API}/{ruta}", params=params, timeout=_TIMEOUT_SECONDS)
            except requests.RequestException:
                if ultimo:
                    raise YouTubeError("YouTube no respondió.") from None
                continue
            if respuesta.status_code >= 500 and not ultimo:
                continue
            if respuesta.status_code >= 400:
                raise YouTubeError(self._motivo(respuesta)) from None
            datos: dict[str, Any] = respuesta.json()
            return datos
        raise YouTubeError("YouTube no respondió.")  # pragma: no cover

    @staticmethod
    def _motivo(respuesta: requests.Response) -> str:
        try:
            error = respuesta.json().get("error", {})
            razon = (error.get("errors") or [{}])[0].get("reason", "")
        except ValueError:
            return f"YouTube respondió {respuesta.status_code}."
        if razon == "quotaExceeded":
            return "Se agotó la cuota diaria de YouTube; se reanuda mañana."
        if razon in ("keyInvalid", "API_KEY_INVALID", "forbidden") or respuesta.status_code == 403:
            return "YouTube rechazó la clave (revisa que esté activa y restringida a YouTube Data API v3)."
        return f"YouTube respondió {respuesta.status_code} ({razon or 'sin detalle'})."

    def resolver_canal(self, referencia: str) -> CanalResuelto:
        ref = referencia.strip()
        params: dict[str, str | int] = {"part": "snippet"}
        m_id = re.search(r"/channel/(UC[\w-]{22})", ref)
        m_handle = re.search(r"@([\w.\-]+)", ref)
        if _ID_CANAL.match(ref):
            params["id"] = ref
        elif m_id:
            params["id"] = m_id.group(1)
        elif m_handle:
            params["forHandle"] = "@" + m_handle.group(1)
        else:
            raise YouTubeError("Usa la dirección del canal, su @usuario o su ID (UC…).")
        items = self._get("channels", **params).get("items") or []
        if not items:
            raise YouTubeError("No encontré ese canal en YouTube.")
        return CanalResuelto(canal_id=items[0]["id"], nombre=items[0]["snippet"]["title"])

    def videos_recientes(
        self, canal_id: str, *, desde: datetime, maximo: int = 50
    ) -> list[VideoYouTube]:
        if not _ID_CANAL.match(canal_id):
            raise YouTubeError("ID de canal inválido.")
        # A channel's uploads playlist id is its channel id with "UC" → "UU".
        datos = self._get(
            "playlistItems",
            part="snippet,contentDetails",
            playlistId="UU" + canal_id[2:],
            maxResults=min(maximo, 50),
        )
        videos: list[VideoYouTube] = []
        for item in datos.get("items", []):
            snippet = item.get("snippet", {})
            if snippet.get("title") in ("Private video", "Deleted video"):
                continue
            publicado = _fecha(
                item.get("contentDetails", {}).get("videoPublishedAt") or snippet["publishedAt"]
            )
            if publicado < desde:
                continue
            videos.append(
                VideoYouTube(
                    video_id=snippet["resourceId"]["videoId"],
                    canal_id=canal_id,
                    titulo=snippet["title"],
                    publicado_en=publicado,
                    miniatura_url=_miniatura(snippet),
                )
            )
        return videos

    def obtener_video(self, referencia: str) -> VideoYouTube:
        video_id = _id_de_video(referencia)
        items = self._get("videos", part="snippet", id=video_id).get("items") or []
        if not items:
            raise YouTubeError("No encontré ese video en YouTube.")
        snippet = items[0]["snippet"]
        return VideoYouTube(
            video_id=video_id,
            canal_id=snippet["channelId"],
            titulo=snippet["title"],
            publicado_en=_fecha(snippet["publishedAt"]),
            miniatura_url=_miniatura(snippet),
        )

    def estadisticas(self, video_ids: list[str]) -> dict[str, int]:
        if not video_ids:
            return {}
        datos = self._get("videos", part="statistics", id=",".join(video_ids[:50]))
        return {
            item["id"]: int(item["statistics"]["viewCount"])
            for item in datos.get("items", [])
            if "viewCount" in item.get("statistics", {})
        }
