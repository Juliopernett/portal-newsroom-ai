"""Domain entity: the commercial identity shown on every client-facing report.

Sprint — Configuración de identidad comercial. Deliberately its own
entity, never a field on `Client` or `Pauta`: this belongs to the medio
that generates reports (Portal Vallenato itself), not to any one commercial
relationship — the same "organic and commercial never converge" instinct
ADR-003 applies to a different axis here (the platform's own identity vs.
the things it manages).

A singleton: there is exactly one row, always addressed by `ID_UNICO` —
never a collection like `Client`/`Pauta`. `logo_storage_key` is an opaque
key into `core.ports.media_storage.MediaStorage` (same Volume `MediaAsset`
already uses) — the actual image bytes never live in this table or in the
browser, so the logo survives across devices/sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

ID_UNICO: Final = "identidad-comercial"


@dataclass(frozen=True, slots=True, kw_only=True)
class IdentidadComercial:
    """The one commercial identity record used to brand every generated report."""

    id: str = ID_UNICO
    nombre_comercial: str
    razon_social: str | None = None
    nit: str | None = None
    telefono: str | None = None
    email: str | None = None
    sitio_web: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    otras_redes: str | None = None
    logo_storage_key: str | None = None
    logo_content_type: str | None = None
    fecha_actualizacion: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.nombre_comercial.strip():
            raise ValueError("nombre_comercial must not be empty")
