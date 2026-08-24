"""Domain entity: which AI provider/model prepares editorial content.

Sprint — configuración de proveedor de IA (2026-08-24). A singleton — exactly
one row, always `ID_UNICO` — same pattern as
`core.entities.identidad_comercial.IdentidadComercial`: an operational
preference belonging to the medio itself, editable from Configuración → IA,
not tied to any one solicitud.

Deliberately holds no secrets. `ANTHROPIC_API_KEY`/`OPENROUTER_API_KEY` still
live only in `.env` (docs/PROJECT_RULES.md rules 2/12) — this entity only
says *which* configured provider/model to use.
`app.api.dependencies.get_ai_provider` falls back to Anthropic + Claude Opus
5 when no row exists yet, same graceful-default spirit already used
throughout `core.services.editorial_ai_service`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

ID_UNICO: Final = "ai-configuracion"


class ProveedorIA(StrEnum):
    """Which adapter `app.api.dependencies.get_ai_provider` constructs."""

    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"


@dataclass(frozen=True, slots=True, kw_only=True)
class AIConfiguracion:
    """The one record saying which AI provider/model to call for editorial prep."""

    id: str = ID_UNICO
    proveedor: ProveedorIA
    modelo: str

    def __post_init__(self) -> None:
        if not self.modelo.strip():
            raise ValueError("modelo must not be empty")
