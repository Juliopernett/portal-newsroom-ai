"""Integration tests: SqlAlchemyPautaRepository against a real SQLite schema."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from core.entities.client import Client, ClientType
from core.entities.pauta import Pauta
from database.repositories.client_repository import SqlAlchemyClientRepository
from database.repositories.pauta_repository import SqlAlchemyPautaRepository


def _client(**overrides: object) -> Client:
    defaults: dict[str, object] = {
        "nombre": "Silvestre Dangond",
        "tipo": ClientType.ARTISTA,
        "telefono": "+573001112233",
    }
    defaults.update(overrides)
    return Client(**defaults)


def _pauta(client_id: str, **overrides: object) -> Pauta:
    defaults: dict[str, object] = {
        "client_id": client_id,
        "fecha_inicio": date(2026, 7, 30),
        "fecha_fin": date(2026, 8, 30),
        "publicaciones_contratadas": 10,
        "valor_pagado": Decimal("500000.00"),
        "fecha_pago": date(2026, 7, 30),
    }
    defaults.update(overrides)
    return Pauta(**defaults)


def test_save_and_get_by_id_round_trips_a_pauta(session: Session) -> None:
    client = _client()
    SqlAlchemyClientRepository(session).save(client)
    repository = SqlAlchemyPautaRepository(session)
    pauta = _pauta(client.id, observaciones="Pago en efectivo")

    repository.save(pauta)
    session.commit()

    assert repository.get_by_id(pauta.id) == pauta


def test_get_by_id_returns_none_when_not_found(session: Session) -> None:
    repository = SqlAlchemyPautaRepository(session)

    assert repository.get_by_id("no-existe") is None


def test_list_all_returns_every_persisted_pauta(session: Session) -> None:
    client_repository = SqlAlchemyClientRepository(session)
    primer_cliente = _client()
    segundo_cliente = _client(telefono="+573009998877")
    client_repository.save(primer_cliente)
    client_repository.save(segundo_cliente)

    repository = SqlAlchemyPautaRepository(session)
    primera = _pauta(primer_cliente.id)
    segunda = _pauta(segundo_cliente.id)
    repository.save(primera)
    repository.save(segunda)
    session.commit()

    resultado = repository.list_all()

    assert {pauta.id for pauta in resultado} == {primera.id, segunda.id}
