"""Integration tests: POST /auth/login, POST /auth/logout, GET /auth/me."""

from __future__ import annotations

from fastapi.testclient import TestClient

from core.entities.user import User
from tests.integration.api.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


def test_login_with_correct_credentials_returns_the_user(
    seeded_user: User, unauthenticated_client: TestClient
) -> None:
    response = unauthenticated_client.post(
        "/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == TEST_USER_EMAIL
    assert body["id"] == seeded_user.id
    assert "password" not in body
    assert "password_hash" not in body


def test_login_sets_a_httponly_session_cookie(
    seeded_user: User, unauthenticated_client: TestClient
) -> None:
    unauthenticated_client.post(
        "/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )

    cookie = next(c for c in unauthenticated_client.cookies.jar if c.name == "session_token")
    assert cookie.value


def test_login_rejects_the_wrong_password(
    seeded_user: User, unauthenticated_client: TestClient
) -> None:
    response = unauthenticated_client.post(
        "/auth/login", json={"email": TEST_USER_EMAIL, "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_rejects_an_unknown_email(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        "/auth/login", json={"email": "no-existe@portalvallenato.com", "password": "anything"}
    )

    assert response.status_code == 401


def test_me_without_a_session_returns_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_a_valid_session_returns_the_user(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == TEST_USER_EMAIL


def test_logout_invalidates_the_session(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 200

    logout_response = client.post("/auth/logout")

    assert logout_response.status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_logout_without_a_session_returns_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post("/auth/logout")

    assert response.status_code == 401


def test_protected_endpoint_without_a_session_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.get("/clients")

    assert response.status_code == 401


def test_protected_endpoint_with_a_session_succeeds(client: TestClient) -> None:
    response = client.get("/clients")

    assert response.status_code == 200
