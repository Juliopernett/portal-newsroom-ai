"""Unit tests for LocalDiskMediaStorage — real filesystem under tmp_path, no network."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.storage.local_disk import LocalDiskMediaStorage, MediaStorageKeyError


def test_init_creates_base_dir_if_missing(tmp_path: Path) -> None:
    base_dir = tmp_path / "media"

    LocalDiskMediaStorage(base_dir)

    assert base_dir.is_dir()


def test_guardar_then_leer_roundtrips_bytes(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)

    storage.guardar("solicitud-1/foto.jpg", b"contenido binario")

    assert storage.leer("solicitud-1/foto.jpg") == b"contenido binario"


def test_guardar_creates_nested_subdirectories(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)

    storage.guardar("a/b/c/archivo.mp4", b"video")

    assert (tmp_path / "a" / "b" / "c" / "archivo.mp4").read_bytes() == b"video"


def test_guardar_overwrites_existing_key(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)
    storage.guardar("key", b"primero")

    storage.guardar("key", b"segundo")

    assert storage.leer("key") == b"segundo"


def test_leer_raises_when_key_does_not_exist(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)

    with pytest.raises(FileNotFoundError):
        storage.leer("no-existe")


def test_eliminar_removes_the_file(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)
    storage.guardar("key", b"contenido")

    storage.eliminar("key")

    assert not (tmp_path / "key").exists()


def test_eliminar_is_a_noop_when_key_does_not_exist(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)

    storage.eliminar("no-existe")  # no debe lanzar


def test_guardar_rejects_key_that_escapes_base_dir(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)

    with pytest.raises(MediaStorageKeyError):
        storage.guardar("../fuera.txt", b"contenido")


def test_leer_rejects_key_that_escapes_base_dir(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)

    with pytest.raises(MediaStorageKeyError):
        storage.leer("../../etc/passwd")


def test_eliminar_rejects_key_that_escapes_base_dir(tmp_path: Path) -> None:
    storage = LocalDiskMediaStorage(tmp_path)

    with pytest.raises(MediaStorageKeyError):
        storage.eliminar("../fuera.txt")
