"""Integration tests: GET /pautas/{pauta_id}/informe.pdf.

Drives the whole stack through real HTTP endpoints — Client, Pauta,
PublicationRequest, DestinoPublicacion — the same objects a real contrato
would have, then downloads the PDF and checks it is a well-formed file.
Content is not parsed (that would just re-implement a PDF reader); what
matters here is that the endpoint builds successfully end-to-end for every
shape the sprint called out, and that it never 500s.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


def _create_client(client: TestClient) -> str:
    response = client.post(
        "/clients",
        json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "+573001112233"},
    )
    return response.json()["id"]


def _create_pauta(client: TestClient, client_id: str, **overrides: object) -> str:
    payload: dict[str, object] = {
        "client_id": client_id,
        "fecha_inicio": "2026-07-30",
        "fecha_fin": "2026-08-30",
        "publicaciones_contratadas": 8,
        "valor_pagado": "280000",
        "fecha_pago": "2026-07-30",
    }
    payload.update(overrides)
    response = client.post("/pautas", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _crear_solicitud_completa_multicanal(
    client: TestClient,
    pauta_id: str,
    titulo: str | None,
    texto: str = "Contenido de la publicación",
) -> str:
    """Create a PublicationRequest linked to `pauta_id`, published on
    WordPress + Facebook + Instagram — the "una solicitud con varios
    destinos" shape from the sprint's test list."""
    solicitud_resp = client.post(
        "/publication-requests",
        json={"pauta_id": pauta_id, "titulo": titulo, "texto": texto},
    )
    assert solicitud_resp.status_code == 201, solicitud_resp.text
    solicitud_id = solicitud_resp.json()["id"]

    wp = client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "wordpress"})
    fb = client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "facebook"})
    ig = client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"})

    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{wp.json()['id']}/confirmar-publicacion",
        json={},
    )
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{fb.json()['id']}/confirmar-publicacion",
        json={"url_publicacion": "https://facebook.com/portalvallenato/posts/1"},
    )
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{ig.json()['id']}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/abc"},
    )
    return solicitud_id


def test_informe_404_when_pauta_does_not_exist(client: TestClient) -> None:
    response = client.get("/pautas/no-existe/informe.pdf")

    assert response.status_code == 404


def test_informe_pauta_sin_publicaciones(client: TestClient) -> None:
    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id)

    response = client.get(f"/pautas/{pauta_id}/informe.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_informe_pauta_con_una_publicacion_multicanal(client: TestClient) -> None:
    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id)
    _crear_solicitud_completa_multicanal(client, pauta_id, "Lanzamiento de sencillo")

    response = client.get(f"/pautas/{pauta_id}/informe.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    # Un solo consumo (no tres) — GET /pautas/{id} usa el mismo PautaService.
    pauta_out = client.get(f"/pautas/{pauta_id}").json()
    assert pauta_out["publicaciones_consumidas"] == 1


def test_informe_solicitud_sin_titulo_no_rompe_la_descarga(client: TestClient) -> None:
    """La columna "Publicación" cae al texto cuando no hay título — nunca vacía."""
    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id)
    _crear_solicitud_completa_multicanal(
        client, pauta_id, titulo=None, texto="Contenido sin título"
    )

    response = client.get(f"/pautas/{pauta_id}/informe.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_informe_pauta_con_varias_publicaciones(client: TestClient) -> None:
    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id)
    for i in range(3):
        _crear_solicitud_completa_multicanal(client, pauta_id, f"Publicación {i}")

    response = client.get(f"/pautas/{pauta_id}/informe.pdf")

    assert response.status_code == 200
    pauta_out = client.get(f"/pautas/{pauta_id}").json()
    assert pauta_out["publicaciones_consumidas"] == 3


def test_informe_pauta_vigente(client: TestClient) -> None:
    client_id = _create_client(client)
    # today() en el entorno de test cae dentro de este rango (ver conftest de la suite).
    pauta_id = _create_pauta(client, client_id, fecha_inicio="2026-07-01", fecha_fin="2030-01-01")

    response = client.get(f"/pautas/{pauta_id}/informe.pdf")

    assert response.status_code == 200
    assert client.get(f"/pautas/{pauta_id}").json()["vigente"] is True


def test_informe_pauta_vencida(client: TestClient) -> None:
    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id, fecha_inicio="2020-01-01", fecha_fin="2020-02-01")

    response = client.get(f"/pautas/{pauta_id}/informe.pdf")

    assert response.status_code == 200
    assert client.get(f"/pautas/{pauta_id}").json()["vencida"] is True


def test_informe_incluye_identidad_comercial_y_logo_cuando_estan_configurados(
    client: TestClient,
) -> None:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(200, 30, 30)).save(buffer, format="PNG")

    client.put("/identidad-comercial", json={"nombre_comercial": "Portal Vallenato"})
    client.post(
        "/identidad-comercial/logo",
        files={"archivo": ("logo.png", io.BytesIO(buffer.getvalue()), "image/png")},
    )

    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id)
    _crear_solicitud_completa_multicanal(client, pauta_id, "Lanzamiento con identidad configurada")

    response = client.get(f"/pautas/{pauta_id}/informe.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_informe_funciona_sin_identidad_comercial_configurada(client: TestClient) -> None:
    """No configurar Identidad comercial nunca debe romper la descarga del informe."""
    client_id = _create_client(client)
    pauta_id = _create_pauta(client, client_id)

    response = client.get(f"/pautas/{pauta_id}/informe.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
