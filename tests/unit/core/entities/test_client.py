"""Unit tests for the Client entity."""

from __future__ import annotations

import pytest

from core.entities.client import Client, ClientType


def _build(**overrides: object) -> Client:
    defaults: dict[str, object] = {
        "nombre": "Silvestre Dangond",
        "tipo": ClientType.ARTISTA,
        "telefono": "+573001112233",
    }
    defaults.update(overrides)
    return Client(**defaults)


def test_create_client_assigns_defaults() -> None:
    client = _build()

    assert client.id
    assert client.instagram is None
    assert client.observaciones is None


def test_create_client_accepts_explicit_values() -> None:
    client = _build(
        id="client-1",
        tipo=ClientType.MANAGER,
        instagram="@silvestredangond",
        observaciones="Cliente frecuente",
    )

    assert client.id == "client-1"
    assert client.tipo == ClientType.MANAGER
    assert client.instagram == "@silvestredangond"
    assert client.observaciones == "Cliente frecuente"


@pytest.mark.parametrize("tipo", list(ClientType))
def test_create_client_accepts_every_client_type(tipo: ClientType) -> None:
    client = _build(tipo=tipo)

    assert client.tipo == tipo


@pytest.mark.parametrize("field_name", ["nombre", "telefono"])
def test_create_client_rejects_empty_required_fields(field_name: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        _build(**{field_name: ""})


def test_client_is_immutable() -> None:
    client = _build()

    with pytest.raises(AttributeError):
        client.nombre = "Otro nombre"  # type: ignore[misc]
