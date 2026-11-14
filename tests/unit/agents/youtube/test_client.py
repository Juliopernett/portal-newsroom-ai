"""Unit tests for agents.youtube.client — requests is mocked, no network."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from agents.youtube.client import YouTubeConfigurationError, YouTubeDataApiReader
from config.settings import Settings
from core.ports.youtube_reader import YouTubeError

CANAL = "UC" + "a" * 22
SECRETA = "CLAVE-SECRETA-123"


def _reader() -> YouTubeDataApiReader:
    return YouTubeDataApiReader(Settings(youtube_api_key=SECRETA, _env_file=None))  # type: ignore[call-arg]


def _resp(json_body: dict, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    return r


def test_missing_key_is_a_configuration_error() -> None:
    with pytest.raises(YouTubeConfigurationError):
        YouTubeDataApiReader(Settings(youtube_api_key=None, _env_file=None))  # type: ignore[call-arg]


def test_recent_videos_come_from_the_uploads_playlist_and_skip_old_and_private() -> None:
    body = {
        "items": [
            {
                "snippet": {
                    "title": "Nueva canción",
                    "publishedAt": "2026-11-01T10:00:00Z",
                    "resourceId": {"videoId": "AAAAAAAAAAA"},
                    "thumbnails": {"medium": {"url": "https://i.ytimg.com/a.jpg"}},
                },
                "contentDetails": {"videoPublishedAt": "2026-11-01T09:00:00Z"},
            },
            {
                "snippet": {
                    "title": "Vieja",
                    "publishedAt": "2025-01-01T10:00:00Z",
                    "resourceId": {"videoId": "BBBBBBBBBBB"},
                }
            },
            {
                "snippet": {
                    "title": "Private video",
                    "publishedAt": "2026-11-02T10:00:00Z",
                    "resourceId": {"videoId": "CCCCCCCCCCC"},
                }
            },
        ]
    }
    with patch("agents.youtube.client.requests.get", return_value=_resp(body)) as get:
        videos = _reader().videos_recientes(CANAL, desde=datetime(2026, 10, 1, tzinfo=UTC))

    assert [v.video_id for v in videos] == ["AAAAAAAAAAA"]
    assert videos[0].miniatura_url == "https://i.ytimg.com/a.jpg"
    assert get.call_args.kwargs["params"]["playlistId"] == "UU" + "a" * 22


def test_details_return_views_and_duration_in_seconds() -> None:
    body = {
        "items": [
            {
                "id": "AAAAAAAAAAA",
                "statistics": {"viewCount": "12345"},
                "contentDetails": {"duration": "PT3M25S"},
            },
            {
                "id": "SHORTSSSSSS",
                "statistics": {"viewCount": "9"},
                "contentDetails": {"duration": "PT45S"},
            },
            {
                "id": "LIVEEEEEEEE",
                "statistics": {"viewCount": "5"},
                "contentDetails": {"duration": "P0D"},
            },
            {"id": "x", "statistics": {}},
        ]
    }
    with patch("agents.youtube.client.requests.get", return_value=_resp(body)):
        d = _reader().detalles(["AAAAAAAAAAA", "SHORTSSSSSS", "LIVEEEEEEEE", "x"])

    assert d["AAAAAAAAAAA"].vistas == 12345 and d["AAAAAAAAAAA"].duracion_segundos == 205
    assert d["SHORTSSSSSS"].duracion_segundos == 45
    assert d["LIVEEEEEEEE"].duracion_segundos is None  # live stream: unknown length
    assert "x" not in d


def test_channel_reference_accepts_handle_url_and_id() -> None:
    body = {"items": [{"id": CANAL, "snippet": {"title": "Canal X"}}]}
    with patch("agents.youtube.client.requests.get", return_value=_resp(body)) as get:
        r = _reader()
        assert r.resolver_canal("@canalx").canal_id == CANAL
        assert get.call_args.kwargs["params"]["forHandle"] == "@canalx"
        r.resolver_canal(f"https://www.youtube.com/channel/{CANAL}")
        assert get.call_args.kwargs["params"]["id"] == CANAL


def test_unknown_reference_is_a_clear_error() -> None:
    with pytest.raises(YouTubeError):
        _reader().resolver_canal("hola mundo")


def test_quota_error_is_readable_and_never_leaks_the_key() -> None:
    body = {"error": {"errors": [{"reason": "quotaExceeded"}]}}
    with (
        patch("agents.youtube.client.requests.get", return_value=_resp(body, 403)),
        pytest.raises(YouTubeError) as err,
    ):
        _reader().detalles(["AAAAAAAAAAA"])

    assert "cuota" in str(err.value).lower() and SECRETA not in str(err.value)


def test_network_failure_does_not_leak_the_key_either() -> None:
    import requests

    boom = requests.ConnectionError(f"https://x/?key={SECRETA}")
    with patch("agents.youtube.client.requests.get", side_effect=boom), pytest.raises(YouTubeError) as err:
        _reader().detalles(["AAAAAAAAAAA"])

    assert SECRETA not in str(err.value)


def test_video_reference_formats() -> None:
    body = {
        "items": [
            {
                "snippet": {
                    "channelId": CANAL,
                    "title": "T",
                    "publishedAt": "2026-11-01T10:00:00Z",
                }
            }
        ]
    }
    with patch("agents.youtube.client.requests.get", return_value=_resp(body)):
        r = _reader()
        for ref in (
            "https://www.youtube.com/watch?v=abcdefghijk",
            "https://youtu.be/abcdefghijk",
            "https://www.youtube.com/shorts/abcdefghijk",
            "abcdefghijk",
        ):
            assert r.obtener_video(ref).video_id == "abcdefghijk"


def test_catalog_pages_through_the_whole_uploads_playlist() -> None:
    def pagina(ids: list[str], siguiente: str | None) -> dict:
        body: dict = {
            "items": [
                {
                    "snippet": {
                        "title": f"Tema {i}",
                        "publishedAt": "2019-01-01T10:00:00Z",
                        "resourceId": {"videoId": i},
                    }
                }
                for i in ids
            ]
        }
        if siguiente:
            body["nextPageToken"] = siguiente
        return body

    respuestas = [_resp(pagina(["AAAAAAAAAAA"], "PAG2")), _resp(pagina(["BBBBBBBBBBB"], None))]
    with patch("agents.youtube.client.requests.get", side_effect=respuestas) as get:
        videos = _reader().catalogo_canal(CANAL)

    assert [v.video_id for v in videos] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]  # old uploads kept
    assert get.call_args_list[1].kwargs["params"]["pageToken"] == "PAG2"


def test_catalog_respects_the_maximum() -> None:
    items = [
        {"snippet": {"title": f"T{i}", "publishedAt": "2020-01-01T00:00:00Z", "resourceId": {"videoId": f"{i:011d}"}}}
        for i in range(50)
    ]
    with patch("agents.youtube.client.requests.get", return_value=_resp({"items": items, "nextPageToken": "X"})):
        assert len(_reader().catalogo_canal(CANAL, maximo=60)) == 60


def test_unavailable_videos_are_the_ids_youtube_does_not_return() -> None:
    cuerpo = {"items": [{"id": "vivo0000001"}]}
    with patch("agents.youtube.client.requests.get", return_value=_resp(cuerpo)) as get:
        ausentes = _reader().videos_no_disponibles(["vivo0000001", "ido00000002"])

    assert ausentes == {"ido00000002"}
    assert get.call_args.kwargs["params"]["part"] == "id"


def test_unavailable_videos_are_checked_in_batches_of_fifty() -> None:
    ids = [f"v{i:010d}" for i in range(120)]
    with patch("agents.youtube.client.requests.get", return_value=_resp({"items": []})) as get:
        ausentes = _reader().videos_no_disponibles(ids)

    assert ausentes == set(ids) and get.call_count == 3
