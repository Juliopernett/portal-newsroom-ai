"""Unit tests for the AIConfiguracion entity."""

from __future__ import annotations

import pytest

from core.entities.ai_configuracion import ID_UNICO, AIConfiguracion, ProveedorIA


def test_create_ai_configuracion_defaults_id_to_id_unico() -> None:
    configuracion = AIConfiguracion(proveedor=ProveedorIA.ANTHROPIC, modelo="claude-opus-5")

    assert configuracion.id == ID_UNICO


def test_create_ai_configuracion_accepts_openrouter() -> None:
    configuracion = AIConfiguracion(
        proveedor=ProveedorIA.OPENROUTER, modelo="deepseek/deepseek-chat"
    )

    assert configuracion.proveedor == ProveedorIA.OPENROUTER
    assert configuracion.modelo == "deepseek/deepseek-chat"


def test_create_ai_configuracion_rejects_empty_modelo() -> None:
    with pytest.raises(ValueError, match="modelo"):
        AIConfiguracion(proveedor=ProveedorIA.ANTHROPIC, modelo="")


def test_create_ai_configuracion_rejects_whitespace_only_modelo() -> None:
    with pytest.raises(ValueError, match="modelo"):
        AIConfiguracion(proveedor=ProveedorIA.ANTHROPIC, modelo="   ")


def test_ai_configuracion_is_immutable() -> None:
    configuracion = AIConfiguracion(proveedor=ProveedorIA.ANTHROPIC, modelo="claude-opus-5")

    with pytest.raises(AttributeError):
        configuracion.modelo = "otro"  # type: ignore[misc]
