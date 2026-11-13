"""Integration tests: Chart Vallenato API (demo YouTube reader, no network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from core.entities.chart import SnapshotVistas


class _CatalogoFalso:
    """Stands in for the website's artist grid; never touches the network."""

    def __init__(self, datos: dict[str, str] | None = None) -> None:
        self.datos = datos or {}

    def obtener(self) -> dict[str, str]:
        return self.datos


@pytest.fixture(autouse=True)
def _sin_red_de_artistas():
    from agents.portal.catalogo_artistas import get_catalogo_artistas
    from app.api.main import app

    app.dependency_overrides[get_catalogo_artistas] = lambda: _CatalogoFalso()
    yield
    app.dependency_overrides.pop(get_catalogo_artistas, None)


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

    estado = {
        v["video_id"]: v["fijado_posicion"] for v in client.get("/chart-vallenato").json()["videos"]
    }
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
    assert set(r.json()) == {"actualizado", "semana_fin", "publicada_en", "filas"}


def test_admin_routes_require_login(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get("/chart-vallenato").status_code == 401
    assert unauthenticated_client.post("/chart-vallenato/recolectar").status_code == 401


def test_collection_stores_the_duration_and_flags_shorts(client: TestClient) -> None:
    from app.api.dependencies import get_unit_of_work
    from app.api.main import app

    _canal(client)
    client.post("/chart-vallenato/recolectar")
    videos = client.get("/chart-vallenato").json()["videos"]

    # The demo reader gives every video a song-like length, so none is a Short.
    assert all(v["duracion_segundos"] and not v["es_short"] for v in videos)

    # A video later found to be 40 s long is flagged and dropped from the ranking.
    from dataclasses import replace

    gen = app.dependency_overrides[get_unit_of_work]()
    uow = next(gen)
    video = uow.chart.get_video(videos[0]["video_id"])
    uow.chart.save_video(replace(video, duracion_segundos=40))
    uow.commit()
    estado = {v["video_id"]: v for v in client.get("/chart-vallenato").json()["videos"]}
    assert estado[videos[0]["video_id"]]["es_short"] is True


def test_embed_can_be_framed_and_always_carries_the_credit(
    unauthenticated_client: TestClient,
) -> None:
    r = unauthenticated_client.get("/chart-vallenato/embed")

    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "x-frame-options" not in r.headers
    assert "frame-ancestors *" in r.headers["content-security-policy"]
    assert "script-src" not in r.headers["content-security-policy"]
    assert "un producto de" in r.text
    assert 'href="https://portalvallenato.com/chart-vallenato/"' in r.text


def test_the_rest_of_the_app_still_refuses_to_be_framed(
    unauthenticated_client: TestClient,
) -> None:
    r = unauthenticated_client.get("/chart-vallenato/publico.json")

    assert r.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_embed_validates_the_row_count(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get("/chart-vallenato/embed?n=2").status_code == 422
    assert unauthenticated_client.get("/chart-vallenato/embed?n=5").status_code == 200


def test_embed_escapes_titles_and_urls() -> None:
    from app.api.routers.chart import _html_embed
    from app.api.schemas.chart import FilaChartOut

    fila = FilaChartOut(
        posicion=1,
        video_id="x",
        titulo='<script>alert(1)</script> "tema"',
        artista="A & B",
        miniatura_url='https://i.ytimg.com/x.jpg" onerror="alert(1)',
        url="https://youtu.be/x",
        vistas_semana=10,
        vistas_totales=20,
        tendencia="sube",
        posicion_anterior=2,
        fijado=False,
        parcial=False,
    )

    salida = _html_embed([fila], None)

    assert "<script>alert" not in salida
    assert "&lt;script&gt;" in salida and "A &amp; B" in salida
    assert 'onerror="alert' not in salida


def _sembrar_cortes() -> None:
    from datetime import date

    from app.api.dependencies import get_unit_of_work
    from app.api.main import app
    from core.entities.chart import CorteVistas, VideoChart

    gen = app.dependency_overrides[get_unit_of_work]()
    uow = next(gen)
    for vid in ("a", "b"):
        uow.chart.save_video(
            VideoChart(
                video_id=vid,
                canal_id="UCx",
                titulo=f"Tema {vid}",
                publicado_en=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        uow.chart.save_corte(CorteVistas(vid, date(2026, 11, 6), 0))
        uow.chart.save_corte(CorteVistas(vid, date(2026, 11, 13), 100 if vid == "a" else 500))
    uow.commit()
    gen.close()


def test_weekly_edition_lifecycle_draft_regenerate_publish(client: TestClient) -> None:
    assert client.get("/chart-vallenato/ediciones").json() == []
    _sembrar_cortes()

    r = client.post("/chart-vallenato/ediciones/2026-11-13/regenerar")
    assert r.status_code == 200, r.text
    ed = r.json()
    assert ed["estado"] == "borrador" and ed["filas"] == 2
    assert [f["video_id"] for f in ed["filas_detalle"]] == ["b", "a"]

    # The editor excludes b and rebuilds the draft.
    client.patch("/chart-vallenato/videos/b", json={"excluido": True})
    rebuilt = client.post("/chart-vallenato/ediciones/2026-11-13/regenerar").json()
    assert [f["video_id"] for f in rebuilt["filas_detalle"]] == ["a"]

    pub = client.post("/chart-vallenato/ediciones/2026-11-13/publicar")
    assert pub.status_code == 200 and pub.json()["estado"] == "publicada"
    assert pub.json()["publicada_en"] is not None
    assert client.post("/chart-vallenato/ediciones/2026-11-13/regenerar").status_code == 409

    lista = client.get("/chart-vallenato/ediciones").json()
    assert [(e["semana_fin"], e["estado"]) for e in lista] == [("2026-11-13", "publicada")]
    assert client.get("/chart-vallenato/ediciones/2026-11-13").json()["filas"] == 1


def test_edition_routes_404_and_require_login(
    client: TestClient, unauthenticated_client: TestClient
) -> None:
    assert client.get("/chart-vallenato/ediciones/2026-11-13").status_code == 404
    assert client.post("/chart-vallenato/ediciones/2026-11-13/regenerar").status_code == 404
    assert client.post("/chart-vallenato/ediciones/2026-11-13/publicar").status_code == 404


def test_public_chart_only_shows_the_published_edition(
    client: TestClient, unauthenticated_client: TestClient
) -> None:
    _sembrar_cortes()
    client.post("/chart-vallenato/ediciones/2026-11-13/regenerar")  # a draft exists

    antes = unauthenticated_client.get("/chart-vallenato/publico.json").json()
    assert antes["filas"] == [] and antes["semana_fin"] is None
    assert "primera edición" in unauthenticated_client.get("/chart-vallenato/embed").text

    client.post("/chart-vallenato/ediciones/2026-11-13/publicar")

    despues = unauthenticated_client.get("/chart-vallenato/publico.json").json()
    assert despues["semana_fin"] == "2026-11-13" and despues["actualizado"] == "2026-11-13"
    assert [f["video_id"] for f in despues["filas"]] == ["b", "a"]
    assert (
        unauthenticated_client.get("/chart-vallenato/publico.json?n=1").json()["filas"][0][
            "video_id"
        ]
        == "b"
    )
    embed = unauthenticated_client.get("/chart-vallenato/embed").text
    assert "Tema b" in embed and "edición del 2026-11-13" in embed
    assert "Datos públicos de YouTube" in embed
    assert "politica-de-privacidad" in embed


def test_public_chart_does_not_expose_the_live_ranking(
    client: TestClient, unauthenticated_client: TestClient
) -> None:
    _canal(client)
    client.post("/chart-vallenato/recolectar")

    assert unauthenticated_client.get("/chart-vallenato/publico.json").json()["filas"] == []


def test_weekly_status_endpoint_needs_login_and_answers(
    client: TestClient, unauthenticated_client: TestClient
) -> None:
    r = client.get("/chart-vallenato/estado-semanal")

    assert r.status_code == 200
    assert set(r.json()) == {"semana_fin", "nivel", "mensaje"}
    assert r.json()["nivel"] in {"ok", "info", "atencion", "error"}


def test_public_rows_link_to_the_artist_page_when_the_website_has_one(
    client: TestClient, unauthenticated_client: TestClient
) -> None:
    from agents.portal.catalogo_artistas import get_catalogo_artistas
    from app.api.dependencies import get_unit_of_work
    from app.api.main import app
    from core.entities.chart import CorteVistas, VideoChart

    app.dependency_overrides[get_catalogo_artistas] = lambda: _CatalogoFalso(
        {"la china laura hamburger": "https://portalvallenato.com/laura-hamburger-la-china/"}
    )
    gen = app.dependency_overrides[get_unit_of_work]()
    uow = next(gen)
    for vid, artista in (("a", "La China"), ("b", "Sin Pagina")):
        uow.chart.save_video(
            VideoChart(
                video_id=vid,
                canal_id="UCx",
                titulo=f"Tema {vid}",
                artista=artista,
                publicado_en=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        from datetime import date

        uow.chart.save_corte(CorteVistas(vid, date(2026, 11, 6), 0))
        uow.chart.save_corte(CorteVistas(vid, date(2026, 11, 13), 100 if vid == "a" else 500))
    uow.commit()
    gen.close()
    client.post("/chart-vallenato/ediciones/2026-11-13/regenerar")
    client.post("/chart-vallenato/ediciones/2026-11-13/publicar")

    filas = {
        f["video_id"]: f
        for f in unauthenticated_client.get("/chart-vallenato/publico.json").json()["filas"]
    }
    assert filas["a"]["artista_url"] == "https://portalvallenato.com/laura-hamburger-la-china/"
    assert filas["b"]["artista_url"] is None
    embed = unauthenticated_client.get("/chart-vallenato/embed").text
    assert 'href="https://portalvallenato.com/laura-hamburger-la-china/"' in embed
    assert "Sin Pagina" in embed
