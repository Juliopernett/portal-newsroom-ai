"""SQLAlchemy adapter for `AIConfiguracionRepository`.

Translates between `core.entities.ai_configuracion.AIConfiguracion` (domain)
and `database.models.ai_configuracion.AIConfiguracionModel` (ORM). The
domain never sees this module.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from core.entities.ai_configuracion import ID_UNICO, AIConfiguracion, ProveedorIA
from database.models.ai_configuracion import AIConfiguracionModel


def _to_model(configuracion: AIConfiguracion) -> AIConfiguracionModel:
    return AIConfiguracionModel(
        id=configuracion.id,
        proveedor=configuracion.proveedor.value,
        modelo=configuracion.modelo,
    )


def _to_domain(model: AIConfiguracionModel) -> AIConfiguracion:
    return AIConfiguracion(
        id=model.id,
        proveedor=ProveedorIA(model.proveedor),
        modelo=model.modelo,
    )


class SqlAlchemyAIConfiguracionRepository:
    """`AIConfiguracionRepository` implemented over a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> AIConfiguracion | None:
        """Return the configured `AIConfiguracion`, or `None` if never set."""
        model = self._session.get(AIConfiguracionModel, ID_UNICO)
        return _to_domain(model) if model is not None else None

    def save(self, configuracion: AIConfiguracion) -> None:
        """Persist `configuracion`, creating or replacing the singleton row."""
        self._session.merge(_to_model(configuracion))
