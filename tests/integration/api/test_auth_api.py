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


def test_login_rejects_an_oversized_password(unauthenticated_client: TestClient) -> None:
    """security audit 2026-08-20, L1 — rejected before it ever reaches Argon2id."""
    response = unauthenticated_client.post(
        "/auth/login", json={"email": TEST_USER_EMAIL, "password": "x" * 257}
    )

    assert response.status_code == 422


def test_login_rejects_an_unknown_email(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        "/auth/login", json={"email": "no-existe@portalvallenato.com", "password": "anything"}
    )

    assert response.status_code == 401


def test_login_blocks_after_too_many_failed_attempts(
    seeded_user: User, unauthenticated_client: TestClient
) -> None:
    for _ in range(5):
        response = unauthenticated_client.post(
            "/auth/login", json={"email": TEST_USER_EMAIL, "password": "wrong-password"}
        )
        assert response.status_code == 401

    blocked = unauthenticated_client.post(
        "/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )

    assert blocked.status_code == 429


def test_login_rate_limit_is_scoped_to_the_email(
    seeded_user: User, unauthenticated_client: TestClient
) -> None:
    for _ in range(5):
        unauthenticated_client.post(
            "/auth/login", json={"email": TEST_USER_EMAIL, "password": "wrong-password"}
        )

    response = unauthenticated_client.post(
        "/auth/login", json={"email": "otra-cuenta@portalvallenato.com", "password": "anything"}
    )

    assert response.status_code == 401  # no 429 — un email distinto no está bloqueado


def test_successful_login_resets_the_failure_count(
    seeded_user: User, unauthenticated_client: TestClient
) -> None:
    for _ in range(4):
        unauthenticated_client.post(
            "/auth/login", json={"email": TEST_USER_EMAIL, "password": "wrong-password"}
        )

    ok = unauthenticated_client.post(
        "/auth/login", json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    )
    assert ok.status_code == 200

    another_attempt = unauthenticated_client.post(
        "/auth/login", json={"email": TEST_USER_EMAIL, "password": "wrong-password"}
    )
    assert another_attempt.status_code == 401  # no 429 — el contador se limpió al entrar


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
