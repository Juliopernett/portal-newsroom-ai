"""Persistence layer (infrastructure).

Implements the `core.ports.repository.Repository` contract on top of
SQLAlchemy. Owns the engine/session (`database.engine`) and, starting with
docs/ROADMAP.md Fase 1, the ORM models (`database/models/`) and concrete
repositories (`database/repositories/`).
"""
