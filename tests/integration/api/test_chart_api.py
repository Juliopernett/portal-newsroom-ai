"""Integration tests: Chart Vallenato API (demo YouTube reader, no network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from core.entities.chart import SnapshotVistas


def _canal(client: TestClient, ref: str = "@silvestredangond", artista: str = "Silvestre") -> str:
    r = client.post("/chart-vallenato/canales", json={"referencia": ref, "artista": artista})
    assert r.status_code == 201, r.text
    canal_id: str = r.json()["canal_id"]
    return canal_id


def test_empty_chart_is_empty_not_an_error(client: TestClient) -> None:
    body = client.get("/chart-vallenato").json()

    assert body["filas"] == [] and body["videos"] == [] and body["actualizado"] is None


def test_add_and_remove_a_channel(client: TestClient) -> None:
    canal_id = _canal(client)

    assert [c["canal_id"] for c in client.get("/chart-vallenato/canales").json()] == [canal_id]
    assert client.delete(f"/chart-vallenato/canales/{canal_id}").status_code == 204
    assert client.get("/chart-vallenato/canales").json() == []
    assert client.delete(f"/chart-vallenato/canales/{canal_id}").status_code == 404


def test_collect_discovers_videos_and_takes_a_snapshot(client: TestClient) -> None:
    _canal(client)

    r = client.post("/chart-vallenato/recolectar")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["canales_ok"] == 1 and body["videos_nuevos"] == 3 and body["snapshots"] == 3
    assert len(client.get("/chart-vallenato").json()["videos"]) == 3
    # Collecting again the same day does not duplicate anything.
    again = client.post("/chart-vallenato/recolectar").json()
    assert again["videos_nuevos"] == 0


def test_exclude_and_pin_survive_a_new_collection(client: TestClient) -> None:
    _canal(client)
    client.post("/chart-vallenato/recolectar")
    videos = client.get("/chart-vallenato").json()["videos"]
    a, b = videos[0]["video_id"], videos[1]["video_id"]

    assert client.patch(f"/chart-vallenato/videos/{a}", json={"excluido": True}).status_code == 200
    assert client.patch(f"/chart-vallenato/videos/{b}", json={"fijar_en": 1}).status_code == 200
    client.post("/chart-vallenato/recolectar")

    estado = {v["video_id"]: v for v in client.get("/chart-vallenato").json()["videos"]}
    assert estado[a]["excluido"] is True
    assert estado[b]["fijado_posicion"] == 1 and estado[b]["excluido"] is False


def test_only_one_video_per_pinned_position(client: TestClient) -> None:
    _canal(client)
    client.post("/chart-vallenato/recolectar")
    a, b = (v["video_id"] for v in client.get("/chart-vallenato").json()["videos"][:2])
    client.patch(f"/chart-vallenato/videos/{a}", json={"fijar_en": 2})

    client.patch(f"/chart-vallenato/videos/{b}", json={"fijar_en": 2})

    estado = {v["video_id"]: v["fijado_posicion"] for v in client.get("/chart-vallenato").json()["videos"]}
    assert estado[b] == 2 and estado[a] is None


def test_manual_video_can_be_added_from_any_channel(client: TestClient) -> None:
    r = client.post(
        "/chart-vallenato/videos",
        json={"referencia": "https://www.youtube.com/watch?v=abcdefghijk", "artista": "Otro"},
    )

    assert r.status_code == 201
    assert r.json()["manual"] is True and r.json()["video_id"] == "abcdefghijk"


def test_chart_ranks_after_enough_daily_history(client: TestClient) -> None:
    """A week of snapshots → a ranked top with views gained, via the real service + repo."""
    from app.api.dependencies import get_unit_of_work
    from app.api.main import app

    _canal(client)
    client.post("/chart-vallenato/recolectar")
    ids = [v["video_id"] for v in client.get("/chart-vallenato").json()["videos"]]
    hoy = datetime.now(UTC).date()
    gen = app.dependency_overrides[get_unit_of_work]()
    uow = next(gen)
    for n, vid in enumerate(ids):
        uow.chart.save_snapshot(SnapshotVistas(vid, hoy - timedelta(days=7), 1_000))
        uow.chart.save_snapshot(SnapshotVistas(vid, hoy, 1_000 + 10_000 * (n + 1)))
    uow.commit()

    body = client.get("/chart-vallenato").json()

    assert [f["vistas_semana"] for f in body["filas"]] == [30_000, 20_000, 10_000]
    assert body["filas"][0]["posicion"] == 1 and body["actualizado"] is not None


def test_public_chart_needs_no_login_and_is_cacheable(
    client: TestClient, unauthenticated_client: TestClient
) -> None:
    r = unauthenticated_client.get(
        "/chart-vallenato/publico.json", headers={"Origin": "https://www.portalvallenato.com"}
    )

    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "https://www.portalvallenato.com"
    assert "max-age" in r.headers["cache-control"]
    assert set(r.json()) == {"actualizado", "filas"}


def test_admin_routes_require_login(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get("/chart-vallenato").status_code == 401
    assert unauthenticated_client.post("/chart-vallenato/recolectar").status_code == 401

