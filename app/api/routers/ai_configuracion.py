"""Routes for AIConfiguracion — la sección Configuración › IA.

`PUT` hace upsert (crea o reemplaza), igual que `identidad_comercial`: es
un singleton (ver `core.entities.ai_configuracion.ID_UNICO`), no hay
"crear otro".

`GET` deliberadamente **no** devuelve 404 cuando nunca se ha configurado
nada — a diferencia de `identidad_comercial` (que no tiene un valor por
defecto razonable para `nombre_comercial`), esta entidad sí tiene uno:
Anthropic + Claude Opus 5, el mismo fallback que
`app.api.dependencies.get_ai_provider` ya aplica cuando no hay fila. Así
el formulario de Configuración siempre puede mostrar el estado activo
real, nunca un formulario vacío para algo que en realidad ya está
funcionando con el default.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agents.ai.anthropic_provider import MODELO_POR_DEFECTO
from app.api.dependencies import get_current_user, get_unit_of_work
from app.api.schemas.ai_configuracion import AIConfiguracionCreate, AIConfiguracionOut
from core.entities.ai_configuracion import ID_UNICO, AIConfiguracion, ProveedorIA
from core.ports.unit_of_work import UnitOfWork

router = APIRouter(
    prefix="/ai-configuracion", tags=["ai-configuracion"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=AIConfiguracionOut)
def obtener_ai_configuracion(uow: UnitOfWork = Depends(get_unit_of_work)) -> AIConfiguracion:
    """Return the configured AI provider/model, or the effective default."""
    configuracion = uow.ai_configuracion.get()
    if configuracion is None:
        return AIConfiguracion(proveedor=ProveedorIA.ANTHROPIC, modelo=MODELO_POR_DEFECTO)
    return configuracion


@router.put("", response_model=AIConfiguracionOut)
def guardar_ai_configuracion(
    payload: AIConfiguracionCreate, uow: UnitOfWork = Depends(get_unit_of_work)
) -> AIConfiguracion:
    """Create or replace which AI provider/model is used for editorial prep."""
    configuracion = AIConfiguracion(id=ID_UNICO, **payload.model_dump())
    uow.ai_configuracion.save(configuracion)
    uow.commit()
    return configuracion
