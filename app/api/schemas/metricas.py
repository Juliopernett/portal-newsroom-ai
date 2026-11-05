"""HTTP schemas for a Pauta's social-media metrics (preview + refresh)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from core.entities.destino_publicacion import CanalPublicacion


class MetricasPostOut(BaseModel):
    alcance: int | None
    vistas: int | None
    reacciones: int | None
    comentarios: int | None
    compartidos: int | None
    guardados: int | None
    interacciones: int | None


class FilaMetricaOut(BaseModel):
    destino_id: str
    solicitud_id: str
    titulo: str
    canal: CanalPublicacion
    url: str | None
    tiene_meta_post_id: bool
    capturado_en: datetime | None
    metricas: MetricasPostOut | None


class ResumenMetricasOut(BaseModel):
    publicaciones_total: int
    publicaciones_con_datos: int
    publicaciones_sin_datos: int
    alcance_total: int | None
    vistas_total: int | None
    interacciones_total: int | None


class MetricasPautaOut(BaseModel):
    """Preview of what the informe would show, plus any per-post refresh errors."""

    incluye_metricas: bool
    resumen: ResumenMetricasOut
    filas: list[FilaMetricaOut]
    errores: list[str] = []
