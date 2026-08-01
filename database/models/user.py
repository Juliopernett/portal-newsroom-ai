"""ORM model for User.

Maps to the `users` table. Deliberately a separate class from
`core.entities.user.User` — see `database/models/client.py` for why.
Translation happens in `database.repositories.user_repository`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class UserModel(Base):
    """Table `users` — one row per team member who can log in."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
