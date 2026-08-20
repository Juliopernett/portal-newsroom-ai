"""Integration tests: SqlAlchemyInformeLinkRepository against a real SQLite schema."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session as SqlAlchemySession

from core.entities.client import Client, ClientType
from core.entities.informe_link import InformeLink
from core.entities.pauta import Pauta
from database.repositories.client_repository import SqlAlchemyClientRepository
from database.repositories.informe_link_repository import SqlAlchemyInformeLinkRepository
from database.repositories.pauta_repository import SqlAlchemyPautaRepository


def _create_pauta(session: SqlAlchemySession, **overrides: object) -> Pauta:
    """Persist a Client and a Pauta so FK-constrained InformeLink tests
    have a real parent — same flush-immediately reasoning
    `test_session_repository._create_user` documents."""
    client = Client(nombre="Silvestre Dangond", tipo=ClientType.ARTISTA, telefono="+573001112233")
    SqlAlchemyClientRepository(session).save(client)
    session.flush()

    defaults: dict[str, object] = {
        "client_id": client.id,
        "fecha_inicio": date(2026, 7, 30),
        "fecha_fin": date(2026, 8, 30),
        "publicaciones_contratadas": 10,
        "valor_pagado": Decimal("500000.00"),
        "fecha_pago": date(2026, 7, 30),
    }
    defaults.update(overrides)
    pauta = Pauta(**defaults)
    SqlAlchemyPautaRepository(session).save(pauta)
    session.flush()
    return pauta


def _informe_link(pauta_id: str, **overrides: object) -> InformeLink:
    now = datetime.now(UTC)
    defaults: dict[str, object] = {
        "pauta_id": pauta_id,
        "token_hash": "abc123",
        "created_at": now,
        "expires_at": now + timedelta(days=15),
    }
    defaults.update(overrides)
    return InformeLink(**defaults)


def test_save_and_get_by_token_hash_round_trips_an_informe_link(session: SqlAlchemySession) -> None:
    pauta = _create_pauta(session)
    repository = SqlAlchemyInformeLinkRepository(session)
    entity = _informe_link(pauta.id, token_hash="a-real-looking-hash")

    repository.save(entity)
    session.commit()

    assert repository.get_by_token_hash("a-real-looking-hash") == entity


def test_get_by_token_hash_returns_none_when_not_found(session: SqlAlchemySession) -> None:
    repository = SqlAlchemyInformeLinkRepository(session)

    assert repository.get_by_token_hash("no-existe") is None
