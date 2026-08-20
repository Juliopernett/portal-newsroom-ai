"""Unit tests for FakeSocialMediaReader."""

from __future__ import annotations

import pytest

from agents.meta_social.fake_reader import FakeSocialMediaReader
from core.entities.destino_publicacion import CanalPublicacion


def test_posts_recientes_returns_only_facebook_posts_for_facebook() -> None:
    posts = FakeSocialMediaReader().posts_recientes(CanalPublicacion.FACEBOOK)

    assert len(posts) > 0
    assert all(p.canal == CanalPublicacion.FACEBOOK for p in posts)


def test_posts_recientes_returns_only_instagram_posts_for_instagram() -> None:
    posts = FakeSocialMediaReader().posts_recientes(CanalPublicacion.INSTAGRAM)

    assert len(posts) > 0
    assert all(p.canal == CanalPublicacion.INSTAGRAM for p in posts)


def test_posts_recientes_marks_every_post_as_demo() -> None:
    """Never mistakable for real data — see agents/meta_social/fake_reader.py."""
    posts = FakeSocialMediaReader().posts_recientes(CanalPublicacion.FACEBOOK)

    assert all(p.texto.startswith("[DEMO]") for p in posts)


def test_posts_recientes_are_sorted_most_recent_first() -> None:
    posts = FakeSocialMediaReader().posts_recientes(CanalPublicacion.FACEBOOK)

    fechas = [p.fecha_publicacion for p in posts]
    assert fechas == sorted(fechas, reverse=True)


def test_posts_recientes_respects_limite() -> None:
    posts = FakeSocialMediaReader().posts_recientes(CanalPublicacion.FACEBOOK, limite=2)

    assert len(posts) == 2


def test_posts_recientes_rejects_wordpress() -> None:
    with pytest.raises(ValueError, match="no hay posts recientes"):
        FakeSocialMediaReader().posts_recientes(CanalPublicacion.WORDPRESS)
