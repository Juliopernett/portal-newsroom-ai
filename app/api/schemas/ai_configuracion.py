"""HTTP schemas for AIConfiguracion."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from core.entities.ai_configuracion import ProveedorIA

_MODELO_MAX = 200


class AIConfiguracionCreate(BaseModel):
    """Request body for `PUT /ai-configuracion`."""

    proveedor: ProveedorIA
    modelo: str = Field(min_length=1, max_length=_MODELO_MAX)


class AIConfiguracionOut(BaseModel):
    """Response body for `AIConfiguracion`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    proveedor: ProveedorIA
    modelo: str
