"""Unit tests for the PostRedSocial entity."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from core.entities.destino_publicacion import CanalPublicacion
from core.entities.post_red_social import PostRedSocial


def _build(**overrides: object) -> PostRedSocial:
    defaults: dict[str, object] = {
        "id": "post-1",
        "canal": CanalPublicacion.FACEBOOK,
        "permalink": "https://www.facebook.com/demo/1",
        "texto": "Un post cualquiera",
        "miniatura_url": None,
        "fecha_publicacion": datetime(2026, 8, 20, tzinfo=UTC),
    }
    defaults.update(overrides)
    return PostRedSocial(**defaults)


def test_create_post_accepts_facebook() -> None:
    post = _build(canal=CanalPublicacion.FACEBOOK)

    assert post.canal == CanalPublicacion.FACEBOOK


def test_create_post_accepts_instagram() -> None:
    post = _build(canal=CanalPublicacion.INSTAGRAM)

    assert post.canal == CanalPublicacion.INSTAGRAM


def test_create_post_rejects_wordpress() -> None:
    with pytest.raises(ValueError, match="canal must be one of"):
        _build(canal=CanalPublicacion.WORDPRESS)


def test_create_post_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="id"):
        _build(id="")


def test_create_post_rejects_empty_permalink() -> None:
    with pytest.raises(ValueError, match="permalink"):
        _build(permalink="")


def test_post_is_immutable() -> None:
    post = _build()

    with pytest.raises(AttributeError):
        post.texto = "otro"  # type: ignore[misc]
