"""Unit tests for the EditorialTask entity."""

from __future__ import annotations

import pytest

from core.entities.editorial_task import EditorialTask, EditorialTaskStatus


def _build(**overrides: object) -> EditorialTask:
    defaults: dict[str, object] = {"article_id": "article-1"}
    defaults.update(overrides)
    return EditorialTask(**defaults)


def test_create_editorial_task_assigns_defaults() -> None:
    task = _build()

    assert task.id
    assert task.status is EditorialTaskStatus.PENDING
    assert task.assigned_to is None
    assert task.priority == 0


def test_create_editorial_task_accepts_explicit_values() -> None:
    task = _build(
        assigned_to="editor@portalvallenato.com",
        priority=3,
        status=EditorialTaskStatus.IN_PROGRESS,
    )

    assert task.assigned_to == "editor@portalvallenato.com"
    assert task.priority == 3
    assert task.status is EditorialTaskStatus.IN_PROGRESS


def test_create_editorial_task_rejects_empty_article_id() -> None:
    with pytest.raises(ValueError, match="article_id"):
        _build(article_id="")


def test_create_editorial_task_rejects_negative_priority() -> None:
    with pytest.raises(ValueError, match="priority"):
        _build(priority=-1)
