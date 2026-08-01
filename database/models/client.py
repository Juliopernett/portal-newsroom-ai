"""ORM model for Client.

Maps to the `clients` table. Deliberately a separate class from
`core.entities.client.Client`, never a subclass of it and never subclassed
by it — the domain entity has no idea SQLAlchemy exists. Translation
between the two happens in `database.repositories.client_repository`.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class ClientModel(Base):
    """Table `clients` — one row per commercial client."""

    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    instagram: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(String, nullable=True)
