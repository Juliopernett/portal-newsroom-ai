"""ORM model for AIConfiguracion.

Maps to the `ai_configuracion` table — a single row, always keyed by
`core.entities.ai_configuracion.ID_UNICO`. Deliberately a separate class
from the domain entity — see `database/models/client.py` for why.
Translation happens in `database.repositories.ai_configuracion_repository`.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class AIConfiguracionModel(Base):
    """Table `ai_configuracion` — one singleton row, which provider/model to call."""

    __tablename__ = "ai_configuracion"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proveedor: Mapped[str] = mapped_column(String(20), nullable=False)
    modelo: Mapped[str] = mapped_column(String(200), nullable=False)
