"""HTTP schemas for IdentidadComercial."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class IdentidadComercialCreate(BaseModel):
    """Request body for `PUT /identidad-comercial` — text fields only, never the logo."""

    nombre_comercial: str
    razon_social: str | None = None
    nit: str | None = None
    telefono: str | None = None
    email: str | None = None
    sitio_web: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    otras_redes: str | None = None


class IdentidadComercialOut(BaseModel):
    """Response body for `IdentidadComercial`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre_comercial: str
    razon_social: str | None
    nit: str | None
    telefono: str | None
    email: str | None
    sitio_web: str | None
    instagram: str | None
    facebook: str | None
    otras_redes: str | None
    logo_storage_key: str | None
    fecha_actualizacion: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tiene_logo(self) -> bool:
        """Whether a logo has been uploaded — the frontend uses this to decide
        whether to render `GET /identidad-comercial/logo` as an `<img>` src."""
        return self.logo_storage_key is not None
