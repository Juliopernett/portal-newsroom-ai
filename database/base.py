"""SQLAlchemy declarative base.

Every ORM model (introduced starting docs/ROADMAP.md Fase 1, e.g.
`database/models/article.py`) must inherit from `Base` so it is picked up
by the shared metadata used for table creation and migrations.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
