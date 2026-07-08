"""Unit tests for the Article entity."""

from __future__ import annotations

import pytest

from core.entities.article import Article, ArticleStatus


def _build(**overrides: object) -> Article:
    defaults: dict[str, object] = {
        "title": "El vallenato silvestre resurge en los pueblos del Cesar",
        "body": "Cuerpo de ejemplo del artículo reescrito.",
        "source": "vallenato-hoy",
    }
    defaults.update(overrides)
    return Article(**defaults)


def test_create_article_assigns_defaults() -> None:
    article = _build()

    assert article.id
    assert article.status is ArticleStatus.DRAFT
    assert article.tags == ()
    assert article.featured_image is None
    assert article.category is None


def test_create_article_accepts_explicit_values() -> None:
    article = _build(
        featured_image="https://vallenatohoy.example.com/img/cover.jpg",
        category="Festival",
        tags=("vallenato", "festival"),
        status=ArticleStatus.PENDING_REVIEW,
    )

    assert article.featured_image is not None
    assert article.category == "Festival"
    assert article.tags == ("vallenato", "festival")
    assert article.status is ArticleStatus.PENDING_REVIEW


def test_create_article_rejects_empty_title() -> None:
    with pytest.raises(ValueError, match="title"):
        _build(title="")


def test_create_article_rejects_empty_source() -> None:
    with pytest.raises(ValueError, match="source"):
        _build(source="")
