"""HTTP schemas for Client."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from core.entities.client import ClientType


class ClientCreate(BaseModel):
    """Request body for `POST /clients`."""

    nombre: str
    tipo: ClientType
    telefono: str
    instagram: str | None = None
    observaciones: str | None = None


class ClientOut(BaseModel):
    """Response body for a `Client`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    tipo: ClientType
    telefono: str
    instagram: str | None
    observaciones: str | None
