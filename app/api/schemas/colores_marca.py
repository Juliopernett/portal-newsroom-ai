"""HTTP schemas for ColoresMarca."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_PATRON = r"^#[0-9A-Fa-f]{6}$"


class ColoresMarcaIn(BaseModel):
    """Request body for `PUT /colores-marca`."""

    fondo: str = Field(pattern=_PATRON)
    destacado: str = Field(pattern=_PATRON)
    texto_destacado: str = Field(pattern=_PATRON)


class ColoresMarcaOut(BaseModel):
    """Response body for `ColoresMarca`."""

    model_config = ConfigDict(from_attributes=True)

    fondo: str
    destacado: str
    texto_destacado: str
