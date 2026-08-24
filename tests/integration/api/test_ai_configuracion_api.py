"""Integration tests: GET/PUT /ai-configuracion."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_returns_the_anthropic_default_before_first_configuration(client: TestClient) -> None:
    """Unlike /identidad-comercial (404), this has a sensible default — see
    app.api.routers.ai_configuracion's module docstring."""
    response = client.get("/ai-configuracion")

    assert response.status_code == 200
    body = response.json()
    assert body["proveedor"] == "anthropic"
    assert body["modelo"] == "claude-opus-5"


def test_put_creates_the_ai_configuracion(client: TestClient) -> None:
    response = client.put(
        "/ai-configuracion", json={"proveedor": "openrouter", "modelo": "deepseek/deepseek-chat"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["proveedor"] == "openrouter"
    assert body["modelo"] == "deepseek/deepseek-chat"


def test_put_is_idempotent_and_replaces_the_singleton(client: TestClient) -> None:
    client.put("/ai-configuracion", json={"proveedor": "anthropic", "modelo": "claude-opus-5"})

    response = client.put(
        "/ai-configuracion", json={"proveedor": "openrouter", "modelo": "meta-llama/llama-3.3-70b"}
    )

    assert response.status_code == 200
    assert client.get("/ai-configuracion").json() == response.json()


def test_put_rejects_an_invalid_proveedor(client: TestClient) -> None:
    response = client.put(
        "/ai-configuracion", json={"proveedor": "openai", "modelo": "gpt-4o-mini"}
    )

    assert response.status_code == 422


def test_put_rejects_an_empty_modelo(client: TestClient) -> None:
    response = client.put("/ai-configuracion", json={"proveedor": "anthropic", "modelo": ""})

    assert response.status_code == 422


def test_ai_configuracion_requires_a_session(client: TestClient) -> None:
    client.cookies.clear()

    assert client.get("/ai-configuracion").status_code == 401
    assert (
        client.put(
            "/ai-configuracion", json={"proveedor": "anthropic", "modelo": "claude-opus-5"}
        ).status_code
        == 401
    )
