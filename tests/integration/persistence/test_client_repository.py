"""Integration tests: SqlAlchemyClientRepository against a real SQLite schema."""

from __future__ import annotations

from sqlalchemy.orm import Session

from core.entities.client import Client, ClientType
from database.repositories.client_repository import SqlAlchemyClientRepository


def _client(**overrides: object) -> Client:
    defaults: dict[str, object] = {
        "nombre": "Silvestre Dangond",
        "tipo": ClientType.ARTISTA,
        "telefono": "+573001112233",
    }
    defaults.update(overrides)
    return Client(**defaults)


def test_save_and_get_by_id_round_trips_a_client(session: Session) -> None:
    repository = SqlAlchemyClientRepository(session)
    client = _client(instagram="@silvestredangond", observaciones="Cliente frecuente")

    repository.save(client)
    session.commit()

    assert repository.get_by_id(client.id) == client


def test_get_by_id_returns_none_when_not_found(session: Session) -> None:
    repository = SqlAlchemyClientRepository(session)

    assert repository.get_by_id("no-existe") is None


def test_save_updates_an_existing_client(session: Session) -> None:
    repository = SqlAlchemyClientRepository(session)
    client = _client()
    repository.save(client)
    session.commit()

    actualizado = _client(id=client.id, nombre="Nombre actualizado")
    repository.save(actualizado)
    session.commit()

    recuperado = repository.get_by_id(client.id)
    assert recuperado is not None
    assert recuperado.nombre == "Nombre actualizado"


def test_list_all_returns_every_persisted_client(session: Session) -> None:
    repository = SqlAlchemyClientRepository(session)
    primero = _client(telefono="+573001112233")
    segundo = _client(telefono="+573009998877")
    repository.save(primero)
    repository.save(segundo)
    session.commit()

    resultado = repository.list_all()

    assert {client.id for client in resultado} == {primero.id, segundo.id}


def test_list_all_returns_an_empty_list_when_no_clients_exist(session: Session) -> None:
    repository = SqlAlchemyClientRepository(session)

    assert repository.list_all() == []
