"""Port for rendering a news cover (portada) image.

Sprint Portadas (2026-10-29). A portada is the 4:5 (1080x1350) branded
image Portal Vallenato puts on WordPress as the featured image and on
social networks: a base photo, a headline, and the brand chrome. It
reproduces the four Canva templates the team already uses
("Noticias"/"Lo último", each with one photo or with a second photo in a
highlight circle). Implemented by `agents.images.pillow_portada_renderer`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class VariantePortada(StrEnum):
    """Which label the cover carries — the two template families."""

    NOTICIAS = "noticias"
    LO_ULTIMO = "lo_ultimo"


class PortadaError(ValueError):
    """The cover cannot be rendered from the given input (unreadable image, empty headline)."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SolicitudPortada:
    """Everything needed to render one cover.

    `imagen_circulo`, when given, selects the "two photos" template: it
    is shown inside a highlight circle with an arrow pointing at it.
    `antetitulo` is an optional bigger first line (e.g. "¡CONFIRMADO!").
    `enfoque_x`/`enfoque_y` (0..1) pick which part of the base photo
    survives the crop to 4:5 — 0.5/0.3 keeps faces, which sit high in
    most photos.
    """

    imagen_base: bytes
    titular: str
    variante: VariantePortada = VariantePortada.NOTICIAS
    antetitulo: str | None = None
    imagen_circulo: bytes | None = None
    enfoque_x: float = 0.5
    enfoque_y: float = 0.3


class PortadaRenderer(Protocol):
    """Contract for rendering a `SolicitudPortada` into image bytes."""

    def renderizar(self, solicitud: SolicitudPortada, *, formato: str = "png") -> bytes:
        """Return the cover as `formato` ("png" or "jpeg") bytes.

        Raises `PortadaError` for input that cannot produce a cover.
        """
        ...
