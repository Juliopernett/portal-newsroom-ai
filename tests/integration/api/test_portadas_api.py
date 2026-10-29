"""Integration tests: POST /portadas — cover rendering from uploaded photos."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image


def _foto() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (800, 600), (200, 120, 40)).save(buffer, "JPEG")
    return buffer.getvalue()


def test_generar_portada_returns_a_png(client: TestClient) -> None:
    response = client.post(
        "/portadas",
        files={"imagen_base": ("foto.jpg", _foto(), "image/jpeg")},
        data={"titular": "Titular de prueba", "variante": "lo_ultimo"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(response.content)).size == (1080, 1350)


def test_generar_portada_with_circle_and_jpeg(client: TestClient) -> None:
    response = client.post(
        "/portadas",
        files={
            "imagen_base": ("a.jpg", _foto(), "image/jpeg"),
            "imagen_circulo": ("b.jpg", _foto(), "image/jpeg"),
        },
        data={"titular": "Titular", "antetitulo": "¡Confirmado!", "formato": "jpeg"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_generar_portada_rejects_a_non_image_with_415(client: TestClient) -> None:
    response = client.post(
        "/portadas",
        files={"imagen_base": ("x.svg", b"<svg/>", "image/svg+xml")},
        data={"titular": "Titular"},
    )

    assert response.status_code == 415


def test_generar_portada_rejects_a_corrupt_image_with_422(client: TestClient) -> None:
    response = client.post(
        "/portadas",
        files={"imagen_base": ("x.jpg", b"basura", "image/jpeg")},
        data={"titular": "Titular"},
    )

    assert response.status_code == 422


def test_generar_portada_requires_login(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        "/portadas",
        files={"imagen_base": ("foto.jpg", _foto(), "image/jpeg")},
        data={"titular": "Titular"},
    )

    assert response.status_code == 401
