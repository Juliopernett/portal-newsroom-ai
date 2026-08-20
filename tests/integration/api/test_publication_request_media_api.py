"""Integration tests: /publication-requests/{id}/media (Sprint 4A, Incremento 7).

`get_media_storage` is overridden to a `LocalDiskMediaStorage` pointed at
`tmp_path` — never the real `Settings().media_storage_dir` (which would
write real files under the project's `database/media/` on every test
run). Same isolation discipline as `get_unit_of_work` in
`tests/integration/api/conftest.py`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agents.storage.local_disk import LocalDiskMediaStorage
from app.api.dependencies import get_media_storage
from app.api.main import app


@pytest.fixture(autouse=True)
def _media_storage_in_tmp_path(tmp_path: Path) -> Iterator[None]:
    storage = LocalDiskMediaStorage(tmp_path / "media")
    app.dependency_overrides[get_media_storage] = lambda: storage
    yield
    # `.pop(..., None)` rather than `del`: `client`'s own teardown
    # (`unauthenticated_client`'s `app.dependency_overrides.clear()`) can
    # run first depending on fixture ordering and already remove this key.
    app.dependency_overrides.pop(get_media_storage, None)


def _crear_solicitud(client: TestClient) -> str:
    response = client.post("/publication-requests", json={"texto": "Anuncio"})
    id_: str = response.json()["id"]
    return id_


def test_subir_media_attaches_an_imagen(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)

    response = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("portada.jpg", b"contenido-fake-jpg", "image/jpeg")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["publication_request_id"] == solicitud_id
    assert body["tipo"] == "imagen"
    assert body["nombre_archivo"] == "portada.jpg"
    assert body["content_type"] == "image/jpeg"
    assert body["tamano_bytes"] == len(b"contenido-fake-jpg")


def test_subir_media_attaches_a_video(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)

    response = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("clip.mp4", b"contenido-fake-mp4", "video/mp4")},
    )

    assert response.status_code == 201
    assert response.json()["tipo"] == "video"


def test_subir_media_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.post(
        "/publication-requests/no-existe/media",
        files={"archivo": ("foto.jpg", b"contenido", "image/jpeg")},
    )

    assert response.status_code == 404


def test_subir_media_rejects_unsupported_content_type(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)

    response = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("audio.mp3", b"contenido", "audio/mpeg")},
    )

    assert response.status_code == 422


def test_subir_media_rejects_svg(client: TestClient) -> None:
    """`image/svg+xml` can carry `<script>`/`onload`, and `descargar_media`
    serves media back with `Content-Disposition: inline` — a closed
    allow-list rejects it before it ever reaches storage (security audit
    2026-08-20, finding H1)."""
    solicitud_id = _crear_solicitud(client)

    response = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={
            "archivo": (
                "logo.svg",
                b"<svg onload=\"alert('xss')\"></svg>",
                "image/svg+xml",
            )
        },
    )

    assert response.status_code == 422


def test_subir_media_rejects_a_file_over_the_imagen_limit(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)
    contenido_grande = b"x" * (10 * 1024 * 1024 + 1)  # 1 byte over the 10 MB default

    response = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("grande.jpg", contenido_grande, "image/jpeg")},
    )

    assert response.status_code == 422


def test_subir_media_rejects_once_solicitud_is_completa(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)
    client.post(f"/publication-requests/{solicitud_id}/destinos", json={"canal": "instagram"})
    destino_id = client.get(f"/publication-requests/{solicitud_id}/destinos").json()[0]["id"]
    client.post(
        f"/publication-requests/{solicitud_id}/destinos/{destino_id}/confirmar-publicacion",
        json={"url_publicacion": "https://instagram.com/p/1"},
    )

    response = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("foto.jpg", b"contenido", "image/jpeg")},
    )

    assert response.status_code == 409


def test_list_media_returns_every_media_asset_for_the_solicitud(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)
    client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("foto.jpg", b"a", "image/jpeg")},
    )
    client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("clip.mp4", b"b", "video/mp4")},
    )

    response = client.get(f"/publication-requests/{solicitud_id}/media")

    assert response.status_code == 200
    nombres = {m["nombre_archivo"] for m in response.json()}
    assert nombres == {"foto.jpg", "clip.mp4"}


def test_list_media_returns_404_when_solicitud_not_found(client: TestClient) -> None:
    response = client.get("/publication-requests/no-existe/media")

    assert response.status_code == 404


def test_descargar_media_returns_the_raw_bytes(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)
    media_id = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("foto.jpg", b"contenido-real", "image/jpeg")},
    ).json()["id"]

    response = client.get(f"/publication-requests/{solicitud_id}/media/{media_id}/contenido")

    assert response.status_code == 200
    assert response.content == b"contenido-real"
    assert response.headers["content-type"] == "image/jpeg"


def test_descargar_media_returns_404_when_media_not_found(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)

    response = client.get(f"/publication-requests/{solicitud_id}/media/no-existe/contenido")

    assert response.status_code == 404


def test_descargar_media_returns_404_when_file_missing_on_disk(
    client: TestClient, tmp_path: Path
) -> None:
    """The DB row survives but the underlying file was removed out-of-band
    (manual disk cleanup, volume reset...) — should read as 404, not 500."""
    solicitud_id = _crear_solicitud(client)
    media_id = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("foto.jpg", b"contenido", "image/jpeg")},
    ).json()["id"]
    (tmp_path / "media" / solicitud_id / media_id).unlink()

    response = client.get(f"/publication-requests/{solicitud_id}/media/{media_id}/contenido")

    assert response.status_code == 404


def test_descargar_media_returns_404_when_media_belongs_to_another_solicitud(
    client: TestClient,
) -> None:
    solicitud_a = _crear_solicitud(client)
    solicitud_b = _crear_solicitud(client)
    media_id = client.post(
        f"/publication-requests/{solicitud_a}/media",
        files={"archivo": ("foto.jpg", b"contenido", "image/jpeg")},
    ).json()["id"]

    response = client.get(f"/publication-requests/{solicitud_b}/media/{media_id}/contenido")

    assert response.status_code == 404


def test_eliminar_media_deletes_it(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)
    media_id = client.post(
        f"/publication-requests/{solicitud_id}/media",
        files={"archivo": ("foto.jpg", b"contenido", "image/jpeg")},
    ).json()["id"]

    response = client.delete(f"/publication-requests/{solicitud_id}/media/{media_id}")

    assert response.status_code == 204
    assert client.get(f"/publication-requests/{solicitud_id}/media").json() == []


def test_eliminar_media_returns_404_when_not_found(client: TestClient) -> None:
    solicitud_id = _crear_solicitud(client)

    response = client.delete(f"/publication-requests/{solicitud_id}/media/no-existe")

    assert response.status_code == 404
