"""Configuración › Colores: saved colours reach every generated image."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

_ROJOS = {"fondo": "#a00000", "destacado": "#00ff00", "texto_destacado": "#000000"}


def _pixel_del_pie(png: bytes) -> tuple[int, ...]:
    return Image.open(io.BytesIO(png)).convert("RGB").getpixel((540, 1340))


def _portada(client: TestClient) -> bytes:
    foto = io.BytesIO()
    Image.new("RGB", (800, 1000), (200, 200, 200)).save(foto, "JPEG")
    response = client.post(
        "/portadas",
        files={"imagen_base": ("foto.jpg", foto.getvalue(), "image/jpeg")},
        data={"titular": "Titular", "antetitulo": "Gancho"},
    )
    assert response.status_code == 200
    return response.content


def test_defaults_to_the_website_colours(client: TestClient) -> None:
    assert client.get("/colores-marca").json() == {
        "fondo": "#3B5998",
        "destacado": "#E1CE26",
        "texto_destacado": "#083A7A",
    }
    assert _pixel_del_pie(_portada(client)) == (59, 89, 152)


def test_saved_colours_are_used_by_new_covers(client: TestClient) -> None:
    assert client.put("/colores-marca", json=_ROJOS).status_code == 200

    assert client.get("/colores-marca").json()["fondo"] == "#A00000"
    assert _pixel_del_pie(_portada(client)) == (160, 0, 0)


@pytest.mark.parametrize("pieza", ["portada", "radar"])
def test_preview_does_not_save_anything(client: TestClient, pieza: str) -> None:
    response = client.get("/colores-marca/vista-previa", params={"pieza": pieza, **_ROJOS})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert client.get("/colores-marca").json()["fondo"] == "#3B5998"


def test_rejects_something_that_is_not_a_colour(client: TestClient) -> None:
    response = client.put("/colores-marca", json={**_ROJOS, "fondo": "azul"})

    assert response.status_code == 422
