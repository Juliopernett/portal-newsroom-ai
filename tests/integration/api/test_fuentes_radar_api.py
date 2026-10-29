"""Integration tests: /radar-fuentes — managing sources and "Escanear ahora".

The feed detector and the adapter factory are overridden with fakes, so no
test here touches the network.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.dependencies import get_detector_feed, get_fabrica_adaptadores
from app.api.main import app
from app.api.routers import fuentes_radar
from core.entities.news_candidate import NewsCandidate
from core.ports.content_source import ResultadoFetch
from core.ports.feed_detector import (
    EntradaFeed,
    FeedDetectado,
    FeedDetectorError,
)


class _Detector:
    def __init__(self, feed: FeedDetectado | None = None, error: str | None = None) -> None:
        self.feed = feed
        self.error = error

    def detectar(self, url: str) -> FeedDetectado | None:
        if self.error:
            raise FeedDetectorError(self.error)
        return self.feed


def _feed(url: str = "https://blogvallenato.com/feed/") -> FeedDetectado:
    return FeedDetectado(
        feed_url=url,
        titulo="Blog Vallenato",
        entradas=(EntradaFeed(titulo="Una nota", publicada=datetime(2026, 10, 28, tzinfo=UTC)),),
    )


class _Adaptador:
    def __init__(self, fuente_id: str) -> None:
        self._id = fuente_id

    def fetch_condicional(self, etag: str | None, last_modified: str | None) -> ResultadoFetch:
        ahora = datetime.now(UTC)
        return ResultadoFetch(
            candidates=[
                NewsCandidate(
                    source=self._id,
                    title="Nota fresca",
                    url="https://blogvallenato.com/nota-1",
                    summary="",
                    hash=f"{self._id}-1",
                    published_at=ahora,
                )
            ],
            etag="e1",
        )


def _con_detector(detector: _Detector) -> None:
    app.dependency_overrides[get_detector_feed] = lambda: detector


def _con_fabrica() -> None:
    app.dependency_overrides[get_fabrica_adaptadores] = lambda: lambda fuente: _Adaptador(fuente.id)


def test_probar_returns_the_detected_feed_without_saving(client: TestClient) -> None:
    _con_detector(_Detector(_feed()))

    response = client.post("/radar-fuentes/probar", json={"url": "blogvallenato.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["feed_url"] == "https://blogvallenato.com/feed/"
    assert body["entradas"][0]["titulo"] == "Una nota"
    assert client.get("/radar-fuentes").json() == []


def test_probar_reports_a_site_without_feed_as_422(client: TestClient) -> None:
    _con_detector(_Detector(None))

    assert client.post("/radar-fuentes/probar", json={"url": "sinrss.com"}).status_code == 422


def test_probar_reports_an_unsafe_address_as_422(client: TestClient) -> None:
    _con_detector(_Detector(error="La dirección apunta a una red interna, no está permitida"))

    response = client.post("/radar-fuentes/probar", json={"url": "http://127.0.0.1/"})

    assert response.status_code == 422
    assert "red interna" in response.json()["detail"]


def test_crear_fuente_saves_the_detected_feed_with_defaults(client: TestClient) -> None:
    _con_detector(_Detector(_feed()))

    response = client.post("/radar-fuentes", json={"url": "blogvallenato.com"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Blog Vallenato"
    assert body["type"] == "rss"
    assert body["url"] == "https://blogvallenato.com/feed/"
    assert (body["intervalo_minutos"], body["max_items"], body["max_age_days"]) == (60, 20, 7)
    assert body["enabled"] is True
    assert len(client.get("/radar-fuentes").json()) == 1


def test_crear_fuente_rejects_a_feed_already_configured(client: TestClient) -> None:
    _con_detector(_Detector(_feed()))
    client.post("/radar-fuentes", json={"url": "blogvallenato.com"})

    response = client.post("/radar-fuentes", json={"url": "https://blogvallenato.com/feed/"})

    assert response.status_code == 409


def test_editar_fuente_toggles_and_updates_limits(client: TestClient) -> None:
    _con_detector(_Detector(_feed()))
    fuente_id = client.post("/radar-fuentes", json={"url": "blogvallenato.com"}).json()["id"]

    response = client.patch(
        f"/radar-fuentes/{fuente_id}", json={"enabled": False, "intervalo_minutos": 120}
    )

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["intervalo_minutos"] == 120
    assert client.patch("/radar-fuentes/no-existe", json={"enabled": True}).status_code == 404


def test_editar_rejects_an_interval_below_the_minimum(client: TestClient) -> None:
    _con_detector(_Detector(_feed()))
    fuente_id = client.post("/radar-fuentes", json={"url": "blogvallenato.com"}).json()["id"]

    assert (
        client.patch(f"/radar-fuentes/{fuente_id}", json={"intervalo_minutos": 1}).status_code
        == 422
    )


def test_escanear_ahora_saves_new_candidates_and_a_second_scan_finds_none(
    client: TestClient,
) -> None:
    _con_detector(_Detector(_feed()))
    _con_fabrica()
    client.post("/radar-fuentes", json={"url": "blogvallenato.com"})

    primero = client.post("/radar-fuentes/escanear")
    segundo = client.post("/radar-fuentes/escanear")

    assert primero.status_code == 200
    assert primero.json()["nuevos_total"] == 1
    assert primero.json()["resultados"][0]["estado"] == "ok"
    assert segundo.json()["nuevos_total"] == 0
    assert segundo.json()["resultados"][0]["duplicados"] == 1
    assert [c["title"] for c in client.get("/discovery").json()] == ["Nota fresca"]
    fuente = client.get("/radar-fuentes").json()[0]
    assert fuente["last_scan"] is not None
    assert fuente["last_error"] is None


def test_escanear_ahora_skips_disabled_sources(client: TestClient) -> None:
    _con_detector(_Detector(_feed()))
    _con_fabrica()
    fuente_id = client.post("/radar-fuentes", json={"url": "blogvallenato.com"}).json()["id"]
    client.patch(f"/radar-fuentes/{fuente_id}", json={"enabled": False})

    response = client.post("/radar-fuentes/escanear")

    assert response.json() == {"resultados": [], "nuevos_total": 0}


def test_escanear_ahora_rejects_a_concurrent_scan_with_409(client: TestClient) -> None:
    _con_fabrica()
    assert fuentes_radar._ESCANEO_EN_CURSO.acquire(blocking=False)
    try:
        response = client.post("/radar-fuentes/escanear")
    finally:
        fuentes_radar._ESCANEO_EN_CURSO.release()

    assert response.status_code == 409


def test_fuentes_require_login(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get("/radar-fuentes").status_code == 401
    assert unauthenticated_client.post("/radar-fuentes/escanear").status_code == 401


def test_crear_fuente_uses_the_domain_when_the_site_title_is_a_whole_sentence(
    client: TestClient,
) -> None:
    largo = FeedDetectado(
        feed_url="https://www.televallenato.com/feeds/posts/default",
        titulo="Noticias, chismes, farándulas y videos vallenato en Internet y televisión",
        entradas=(EntradaFeed(titulo="Nota", publicada=None),),
    )
    _con_detector(_Detector(largo))

    response = client.post("/radar-fuentes", json={"url": "televallenato.com"})

    assert response.json()["name"] == "televallenato.com"
