"""SQLAlchemy adapter for `core.ports.pauta_repository.PautaRepository`.

Translates between `core.entities.pauta.Pauta` (domain) and
`database.models.pauta.PautaModel` (ORM). The domain never sees this
module.
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.entities.pauta import Pauta
from database.models.pauta import PautaModel


def _to_model(pauta: Pauta) -> PautaModel:
    return PautaModel(
        id=pauta.id,
        client_id=pauta.client_id,
        fecha_inicio=pauta.fecha_inicio,
        fecha_fin=pauta.fecha_fin,
        publicaciones_contratadas=pauta.publicaciones_contratadas,
        valor_pagado=pauta.valor_pagado,
        fecha_pago=pauta.fecha_pago,
        saldo_pendiente=pauta.saldo_pendiente,
        fecha_registro=pauta.fecha_registro,
        observaciones=pauta.observaciones,
    )


def _to_domain(model: PautaModel) -> Pauta:
    fecha_registro = model.fecha_registro
    if fecha_registro.tzinfo is None:
        # SQLite drops tzinfo on round trip (Postgres does not) — see
        # database.repositories.publication_request_repository for the
        # same fix, applied there first.
        fecha_registro = fecha_registro.replace(tzinfo=UTC)
    return Pauta(
        id=model.id,
        client_id=model.client_id,
        fecha_inicio=model.fecha_inicio,
        fecha_fin=model.fecha_fin,
        publicaciones_contratadas=model.publicaciones_contratadas,
        valor_pagado=model.valor_pagado,
        fecha_pago=model.fecha_pago,
        saldo_pendiente=model.saldo_pendiente,
        fecha_registro=fecha_registro,
        observaciones=model.observaciones,
    )


class SqlAlchemyPautaRepository:
    """`PautaRepository` implemented on top of a SQLAlchemy `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, pauta: Pauta) -> None:
        """Persist `pauta`, creating or updating it as needed."""
        self._session.merge(_to_model(pauta))

    def get_by_id(self, id: str) -> Pauta | None:
        """Return the `Pauta` identified by `id`, or `None` if not found."""
        model = self._session.get(PautaModel, id)
        return _to_domain(model) if model is not None else None

    def list_all(self) -> list[Pauta]:
        """Return every `Pauta` — the input `pautas_por_vencer` needs."""
        models = self._session.execute(select(PautaModel)).scalars().all()
        return [_to_domain(model) for model in models]
