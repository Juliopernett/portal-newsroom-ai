"""Integration tests: GET/PUT /identidad-comercial, POST/GET /identidad-comercial/logo."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "nombre_comercial": "Portal Vallenato",
        "razon_social": "Portal Vallenato SAS",
        "nit": "900.123.456-7",
        "telefono": "+573000000000",
        "email": "contacto@portalvallenato.com",
        "sitio_web": "https://portalvallenato.com",
        "instagram": "@portalvallenato",
        "facebook": "PortalVallenato",
        "otras_redes": "TikTok: @portalvallenato",
    }
    payload.update(overrides)
    return payload


def _tiny_png() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(200, 30, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_get_returns_404_before_first_configuration(client: TestClient) -> None:
    response = client.get("/identidad-comercial")

    assert response.status_code == 404


def test_put_creates_the_identidad_comercial(client: TestClient) -> None:
    response = client.put("/identidad-comercial", json=_payload())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["nombre_comercial"] == "Portal Vallenato"
    assert body["nit"] == "900.123.456-7"
    assert body["tiene_logo"] is False


def test_put_is_idempotent_and_replaces_text_fields(client: TestClient) -> None:
    client.put("/identidad-comercial", json=_payload())

    response = client.put(
        "/identidad-comercial", json=_payload(nombre_comercial="Portal Vallenato Radio")
    )

    assert response.status_code == 200
    assert response.json()["nombre_comercial"] == "Portal Vallenato Radio"
    # Sigue siendo una sola fila — GET nunca devuelve más de un registro.
    assert client.get("/identidad-comercial").json()["nombre_comercial"] == "Portal Vallenato Radio"


def test_logo_upload_requires_identidad_configured_first(client: TestClient) -> None:
    response = client.post(
        "/identidad-comercial/logo",
        files={"archivo": ("logo.png", io.BytesIO(_tiny_png()), "image/png")},
    )

    assert response.status_code == 404


def test_logo_upload_rejects_non_image_content_type(client: TestClient) -> None:
    client.put("/identidad-comercial", json=_payload())

    response = client.post(
        "/identidad-comercial/logo",
        files={"archivo": ("logo.txt", io.BytesIO(b"no es una imagen"), "text/plain")},
    )

    assert response.status_code == 422


def test_logo_upload_rejects_svg(client: TestClient) -> None:
    """`descargar_logo` is public and serves the logo inline — an accepted
    SVG would run in the browser for anyone visiting the login page
    (security audit 2026-08-20, finding M2)."""
    client.put("/identidad-comercial", json=_payload())

    response = client.post(
        "/identidad-comercial/logo",
        files={
            "archivo": (
                "logo.svg",
                io.BytesIO(b"<svg onload=\"alert('xss')\"></svg>"),
                "image/svg+xml",
            )
        },
    )

    assert response.status_code == 422


def test_logo_upload_then_download_round_trips_bytes(client: TestClient) -> None:
    client.put("/identidad-comercial", json=_payload())
    contenido = _tiny_png()

    upload = client.post(
        "/identidad-comercial/logo",
        files={"archivo": ("logo.png", io.BytesIO(contenido), "image/png")},
    )
    assert upload.status_code == 200
    assert upload.json()["tiene_logo"] is True

    descarga = client.get("/identidad-comercial/logo")
    assert descarga.status_code == 200
    assert descarga.headers["content-type"] == "image/png"
    assert descarga.content == contenido


def test_replacing_logo_does_not_orphan_the_previous_one(client: TestClient) -> None:
    client.put("/identidad-comercial", json=_payload())
    primero = _tiny_png()
    client.post(
        "/identidad-comercial/logo", files={"archivo": ("a.png", io.BytesIO(primero), "image/png")}
    )

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color=(10, 200, 10)).save(buffer, format="PNG")
    segundo = buffer.getvalue()
    client.post(
        "/identidad-comercial/logo", files={"archivo": ("b.png", io.BytesIO(segundo), "image/png")}
    )

    descarga = client.get("/identidad-comercial/logo")
    assert descarga.content == segundo


def test_saving_text_fields_again_preserves_the_existing_logo(client: TestClient) -> None:
    client.put("/identidad-comercial", json=_payload())
    contenido = _tiny_png()
    client.post(
        "/identidad-comercial/logo",
        files={"archivo": ("logo.png", io.BytesIO(contenido), "image/png")},
    )

    client.put("/identidad-comercial", json=_payload(telefono="+573001112233"))

    assert client.get("/identidad-comercial").json()["tiene_logo"] is True
    assert client.get("/identidad-comercial/logo").content == contenido


def test_logo_get_returns_404_when_never_uploaded(client: TestClient) -> None:
    client.put("/identidad-comercial", json=_payload())

    response = client.get("/identidad-comercial/logo")

    assert response.status_code == 404


def test_logo_get_works_without_a_session(client: TestClient) -> None:
    """The logo is public branding (login screen, sidebar, favicon) — unlike
    every other identidad-comercial field, it must render before login.

    Configures it through the already-logged-in `client` fixture, then
    drops its session cookie to simulate an unauthenticated request — the
    same TestClient, just without the cookie `client`'s login left behind.
    """
    client.put("/identidad-comercial", json=_payload())
    contenido = _tiny_png()
    client.post(
        "/identidad-comercial/logo",
        files={"archivo": ("logo.png", io.BytesIO(contenido), "image/png")},
    )

    client.cookies.clear()
    response = client.get("/identidad-comercial/logo")

    assert response.status_code == 200
    assert response.content == contenido


def test_identidad_comercial_text_fields_still_require_a_session(client: TestClient) -> None:
    client.cookies.clear()

    assert client.get("/identidad-comercial").status_code == 401
    assert client.put("/identidad-comercial", json=_payload()).status_code == 401
