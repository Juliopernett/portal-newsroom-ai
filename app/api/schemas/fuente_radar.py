"""HTTP schemas for Radar sources and scans (Sprint Fuentes, 2026-10-29)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FuenteRadarOut(BaseModel):
    """Response body for a configured `Source`."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    url: str
    enabled: bool
    last_scan: datetime | None
    intervalo_minutos: int
    max_items: int
    max_age_days: int
    last_error: str | None
    errores_consecutivos: int
    last_new_count: int


class FuenteRadarCreate(BaseModel):
    """Request body to add a source: a site or feed address, the rest has defaults."""

    url: str = Field(min_length=4, max_length=500)
    name: str | None = Field(default=None, max_length=120)
    intervalo_minutos: int = Field(default=60, ge=5, le=10080)
    max_items: int = Field(default=20, ge=1, le=100)
    max_age_days: int = Field(default=7, ge=1, le=90)


class FuenteRadarUpdate(BaseModel):
    """Request body to edit a source — every field optional."""

    enabled: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    intervalo_minutos: int | None = Field(default=None, ge=5, le=10080)
    max_items: int | None = Field(default=None, ge=1, le=100)
    max_age_days: int | None = Field(default=None, ge=1, le=90)


class ProbarFuenteIn(BaseModel):
    """Request body to preview what a URL would give, without saving anything."""

    url: str = Field(min_length=4, max_length=500)


class EntradaPreviaOut(BaseModel):
    titulo: str
    publicada: datetime | None


class ProbarFuenteOut(BaseModel):
    feed_url: str
    titulo: str
    entradas: list[EntradaPreviaOut]


class ResultadoEscaneoOut(BaseModel):
    """What scanning one source did."""

    model_config = ConfigDict(from_attributes=True)

    fuente_id: str
    fuente: str
    estado: str
    consultados: int
    nuevos: int
    duplicados: int
    error: str | None


class EscaneoOut(BaseModel):
    resultados: list[ResultadoEscaneoOut]
    nuevos_total: int
