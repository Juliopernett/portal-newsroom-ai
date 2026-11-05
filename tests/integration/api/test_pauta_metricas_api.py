"""Integration tests: opt-in social metrics for a Pauta's informe.

GET /pautas/{id}/metricas (internal preview), POST .../metricas/actualizar
(bulk refresh from Meta — the demo reader in tests) and the informe PDF
only carrying the block when the contract opts in.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _hoy_fijo(congelar_hoy: None) -> None:
    """Hard-coded 2026-07/08 Pauta dates assume "today" is early August 2026."""


def _pauta(client: TestClient, **overrides: object) -> str:
    client_id = client.post(
        "/clients", json={"nombre": "Silvestre Dangond", "tipo": "artista", "telefono": "300"}
    ).json()["id"]
    payload: dict[str, object] = {
        "client_id": client_id,
        "fecha_inicio": "2026-07-30",
        "fecha_fin": "2026-08-30",
        "publicaciones_contratadas": 10,
        "valor_pagado": "500000.00",
        "fecha_pago": "2026-07-30",
    }
    payload.update(overrides)
    response = client.post("/pautas", json=payload)
    assert response.status_code == 201, response.text
    pauta_id: str = response.json()["id"]
    return pauta_id


def _publicada(client: TestClient, pauta_id: str, canal: str, meta_post_id: str | None) -> None:
    """One solicitud of this pauta, published on `canal`."""
    solicitud_id = client.post(
        "/publication-requests",
        json={"pauta_id": pauta_id, "texto": "Anuncio", "titulo": f"Nota {canal}"},
    ).json()["id"]
    destino_id = client.post(
        f"/publication-requests/{solicitud_id}/destinos", json={"canal": canal}
    ).json()["id"]
    body: dict[str, object] = {"url_publicacion": f"https://{canal}.com/p/1"}
    if meta_post_id:
        body["meta_post_id"] = meta_post_id
    response = client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json=body,
    )
    assert response.status_code == 200, response.text


def test_incluye_metricas_defaults_to_false_and_round_trips(client: TestClient) -> None:
    pauta_id = _pauta(client)
    assert client.get(f"/pautas/{pauta_id}").json()["incluye_metricas"] is False

    pauta = client.get(f"/pautas/{pauta_id}").json()
    payload = {
        k: pauta[k]
        for k in (
            "client_id",
            "fecha_inicio",
            "fecha_fin",
            "publicaciones_contratadas",
            "valor_pagado",
            "fecha_pago",
        )
    }
    updated = client.put(f"/pautas/{pauta_id}", json={**payload, "incluye_metricas": True})

    assert updated.status_code == 200
    assert updated.json()["incluye_metricas"] is True


def test_preview_before_any_refresh_has_no_numbers(client: TestClient) -> None:
    pauta_id = _pauta(client)
    _publicada(client, pauta_id, "facebook", "pagina_123")

    body = client.get(f"/pautas/{pauta_id}/metricas").json()

    assert body["resumen"]["publicaciones_total"] == 1
    assert body["resumen"]["publicaciones_con_datos"] == 0
    assert body["resumen"]["alcance_total"] is None  # not measured is NOT zero
    assert body["filas"][0]["metricas"] is None


def test_refresh_saves_metrics_and_summarizes_them(client: TestClient) -> None:
    pauta_id = _pauta(client)
    _publicada(client, pauta_id, "facebook", "pagina_123")
    _publicada(client, pauta_id, "instagram", "17890")

    response = client.post(f"/pautas/{pauta_id}/metricas/actualizar")

    assert response.status_code == 200
    body = response.json()
    assert body["errores"] == []
    assert body["resumen"]["publicaciones_con_datos"] == 2
    assert body["resumen"]["alcance_total"] > 0
    assert body["resumen"]["interacciones_total"] > 0
    # Persisted: a plain GET returns the same numbers without calling Meta.
    again = client.get(f"/pautas/{pauta_id}/metricas").json()
    assert again["resumen"] == body["resumen"]


def test_refresh_skips_posts_without_a_meta_post_id(client: TestClient) -> None:
    pauta_id = _pauta(client)
    _publicada(client, pauta_id, "facebook", None)  # link pasted by hand, no post picked

    body = client.post(f"/pautas/{pauta_id}/metricas/actualizar").json()

    assert body["resumen"]["publicaciones_total"] == 1
    assert body["resumen"]["publicaciones_sin_datos"] == 1
    assert body["filas"][0]["tiene_meta_post_id"] is False


def test_metricas_unknown_pauta_is_404(client: TestClient) -> None:
    assert client.get("/pautas/no-existe/metricas").status_code == 404
    assert client.post("/pautas/no-existe/metricas/actualizar").status_code == 404


def _pdf_text(client: TestClient, pauta_id: str) -> bytes:
    response = client.get(f"/pautas/{pauta_id}/informe.pdf")
    assert response.status_code == 200
    return response.content


def test_informe_pdf_only_includes_the_metrics_block_when_the_contract_opts_in(
    client: TestClient,
) -> None:
    pauta_id = _pauta(client)
    _publicada(client, pauta_id, "instagram", "17890")
    client.post(f"/pautas/{pauta_id}/metricas/actualizar")
    sin_optar = _pdf_text(client, pauta_id)

    pauta = client.get(f"/pautas/{pauta_id}").json()
    payload = {
        k: pauta[k]
        for k in (
            "client_id",
            "fecha_inicio",
            "fecha_fin",
            "publicaciones_contratadas",
            "valor_pagado",
            "fecha_pago",
        )
    }
    client.put(f"/pautas/{pauta_id}", json={**payload, "incluye_metricas": True})
    con_metricas = _pdf_text(client, pauta_id)

    # The opted-in report is a real PDF with an extra section, so it is larger.
    assert con_metricas.startswith(b"%PDF") and sin_optar.startswith(b"%PDF")
    assert len(con_metricas) > len(sin_optar)
