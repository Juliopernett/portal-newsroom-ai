"""Canned `YouTubeReader` — tests and local demos, no network, no API key.

Every title is prefixed `[DEMO]` so nothing here can be mistaken for real
data (same discipline as `agents.meta_social.fake_reader`). View counts grow
deterministically with the calendar day, so a few daily runs produce a real
looking ranking.
"""

from __future__ import annotations

import zlib
from datetime import UTC, date, datetime, timedelta

from core.ports.youtube_reader import CanalResuelto, DetalleVideo, VideoYouTube, YouTubeError


def _n(texto: str, modulo: int) -> int:
    return zlib.crc32(texto.encode()) % modulo


class FakeYouTubeReader:
    def __init__(self, *, hoy: date | None = None, canal_con_error: str | None = None) -> None:
        self._hoy = hoy
        self._canal_con_error = canal_con_error

    def _dia(self) -> int:
        return (self._hoy or datetime.now(UTC).date()).toordinal()

    def resolver_canal(self, referencia: str) -> CanalResuelto:
        ref = referencia.strip()
        if not ref:
            raise YouTubeError("Referencia vacía.")
        canal_id = ref if ref.startswith("UC") else "UC" + f"{_n(ref, 10**11):022d}"[:22]
        return CanalResuelto(canal_id=canal_id, nombre=f"[DEMO] Canal {ref.lstrip('@')[:30]}")

    def videos_recientes(
        self, canal_id: str, *, desde: datetime, maximo: int = 50
    ) -> list[VideoYouTube]:
        if canal_id == self._canal_con_error:
            raise YouTubeError("canal de prueba con error")
        base = datetime.combine(
            self._hoy or datetime.now(UTC).date(), datetime.min.time(), tzinfo=UTC
        )
        return [
            VideoYouTube(
                video_id=f"demo{_n(canal_id + str(i), 10**7):07d}",
                canal_id=canal_id,
                titulo=f"[DEMO] Canción {i + 1} de {canal_id[-4:]}",
                publicado_en=base - timedelta(days=10 * (i + 1)),
                miniatura_url=None,
            )
            for i in range(3)
        ]

    def catalogo_canal(self, canal_id: str, *, maximo: int = 500) -> list[VideoYouTube]:
        if canal_id == self._canal_con_error:
            raise YouTubeError("canal de prueba con error")
        base = datetime.combine(
            self._hoy or datetime.now(UTC).date(), datetime.min.time(), tzinfo=UTC
        )
        return [
            VideoYouTube(
                video_id=f"demo{_n(canal_id + str(i), 10**7):07d}",
                canal_id=canal_id,
                titulo=f"[DEMO] Canción {i + 1} de {canal_id[-4:]}",
                publicado_en=base - timedelta(days=10 * (i + 1)),
                miniatura_url=None,
            )
            for i in range(5)
        ][:maximo]

    def obtener_video(self, referencia: str) -> VideoYouTube:
        vid = referencia.strip()[-11:]
        return VideoYouTube(
            video_id=vid,
            canal_id="UC" + "0" * 22,
            titulo=f"[DEMO] Video {vid}",
            publicado_en=datetime.now(UTC) - timedelta(days=5),
        )

    def detalles(self, video_ids: list[str]) -> dict[str, DetalleVideo]:
        return {
            vid: DetalleVideo(
                vistas=50_000 + _n(vid, 400_000) + self._dia() * (200 + _n(vid, 3_000)),
                duracion_segundos=200 + _n(vid, 120),
            )
            for vid in video_ids
        }
