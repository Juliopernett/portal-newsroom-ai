"""HTTP schemas for the PublicationRequest report.

Sprint 4A, Incremento 6 (see docs/adr/ADR-006-multichannel-publication.md).
Mirrors `core.services.reporte_service.ReporteSolicitud`/`ReporteDestino`
field for field — this schema exists only to serialize what that pure
function already built, same convention every other `*Out` schema in
`app/api/schemas/` already follows.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.entities.destino_publicacion import CanalPublicacion, EstadoDestino


class ReporteDestinoOut(BaseModel):
    """One destino's row in a PublicationRequest's report."""

    model_config = ConfigDict(from_attributes=True)

    canal: CanalPublicacion
    estado: EstadoDestino
    enlace: str | None
    fecha_publicacion: datetime | None
    ultimo_error: str | None


class ReporteSolicitudOut(BaseModel):
    """Response body for `GET /publication-requests/{id}/reporte`."""

    model_config = ConfigDict(from_attributes=True)

    publication_request_id: str
    titulo: str | None
    texto: str
    cliente_nombre: str | None
    pauta_id: str | None
    fecha_recepcion: datetime
    fecha_cierre: datetime | None
    completa: bool
    pauta_consumida: bool
    destinos: list[ReporteDestinoOut]
