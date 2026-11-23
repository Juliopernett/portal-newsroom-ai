"""Port for the supporting numbers other music platforms give for a song.

These never change the chart position (that is YouTube views only); they are
extra information for the editor: how the same song does on Spotify/Deezer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ApoyoCancion:
    """What a platform says about one song: an index plus the link to it."""

    plataforma: str  # "spotify" | "deezer"
    valor: int  # Spotify popularity 0-100; Deezer rank (higher = more popular)
    url: str


class BuscadorMusica(Protocol):
    plataforma: str

    def buscar(self, artista: str, titulo: str) -> ApoyoCancion | None:
        """Find the song and return its figure, or None when there is no confident match."""
        ...
