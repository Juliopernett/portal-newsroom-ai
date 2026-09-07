"""Integration tests: GET /pautas/{pauta_id}/contrato.pdf and its share link.

Mirrors `test_informe_pauta_api.py` for the contract-terms document — the
one sent to the client when the pauta is about to start. Content is not
parsed; what matters is that the endpoint builds end-to-end for every
shape and never 500s, and that the token-guarded public route behaves
exactly like the informe one.
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
        "fecha_inicio": "2026-09-10",
        "fecha_fin": "2026-10-10",
        "publicaciones_contratadas": 8,
        "valor_pagado": "280000",
        "fecha_pago": "2026-09-10",
    }
    payload.update(overrides)
    response = client.post("/pautas", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_contrato_404_when_pauta_does_not_exist(client: TestClient) -> None:
    assert client.get("/pautas/no-existe/contrato.pdf").status_code == 404


def test_contrato_pdf_se_descarga(client: TestClient) -> None:
    pauta_id = _create_pauta(client, _create_client(client))

    response = client.get(f"/pautas/{pauta_id}/contrato.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "contrato-Silvestre-Dangond" in response.headers["content-disposition"]


def test_contrato_pdf_con_saldo_pendiente_y_observaciones(client: TestClient) -> None:
    pauta_id = _create_pauta(
        client,
        _create_client(client),
        saldo_pendiente="120000",
        observaciones="Incluye pauta en historia de Instagram",
    )

    response = client.get(f"/pautas/{pauta_id}/contrato.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_contrato_pdf_funciona_sin_identidad_comercial(client: TestClient) -> None:
    pauta_id = _create_pauta(client, _create_client(client))

    response = client.get(f"/pautas/{pauta_id}/contrato.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_contrato_pdf_incluye_identidad_y_logo_configurados(client: TestClient) -> None:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color=(200, 30, 30)).save(buffer, format="PNG")
    client.put("/identidad-comercial", json={"nombre_comercial": "Portal Vallenato"})
    client.post(
        "/identidad-comercial/logo",
        files={"archivo": ("logo.png", io.BytesIO(buffer.getvalue()), "image/png")},
    )
    pauta_id = _create_pauta(client, _create_client(client))

    response = client.get(f"/pautas/{pauta_id}/contrato.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


# --- Enlace compartible (POST .../contrato-link + GET .../contrato-publico.pdf) ---


def test_crear_contrato_link_404_when_pauta_does_not_exist(client: TestClient) -> None:
    assert client.post("/pautas/no-existe/contrato-link").status_code == 404


def test_crear_contrato_link_devuelve_url_publica_y_expiracion(client: TestClient) -> None:
    pauta_id = _create_pauta(client, _create_client(client))

    body = client.post(f"/pautas/{pauta_id}/contrato-link").json()

    assert f"/pautas/{pauta_id}/contrato-publico.pdf?token=" in body["url"]
    assert body["expira_en"]


def test_contrato_publico_pdf_se_abre_sin_sesion(client: TestClient) -> None:
    pauta_id = _create_pauta(client, _create_client(client))
    token = client.post(f"/pautas/{pauta_id}/contrato-link").json()["url"].split("token=")[1]

    from app.api.main import app as fastapi_app

    with TestClient(fastapi_app) as publico:
        response = publico.get(f"/pautas/{pauta_id}/contrato-publico.pdf", params={"token": token})

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_contrato_publico_pdf_404_con_token_basura(client: TestClient) -> None:
    pauta_id = _create_pauta(client, _create_client(client))

    response = client.get(
        f"/pautas/{pauta_id}/contrato-publico.pdf", params={"token": "no-es-un-token"}
    )

    assert response.status_code == 404


def test_contrato_publico_pdf_404_cuando_el_token_es_de_otra_pauta(client: TestClient) -> None:
    client_id = _create_client(client)
    pauta_a = _create_pauta(client, client_id)
    pauta_b = _create_pauta(client, client_id, fecha_inicio="2026-11-01", fecha_fin="2026-11-30")
    token = client.post(f"/pautas/{pauta_a}/contrato-link").json()["url"].split("token=")[1]

    response = client.get(f"/pautas/{pauta_b}/contrato-publico.pdf", params={"token": token})

    assert response.status_code == 404
