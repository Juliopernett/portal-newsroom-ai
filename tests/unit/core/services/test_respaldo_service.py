"""Unit tests for the nightly backup (service, S3 adapter and pg_dump command)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import ClientError

from agents.storage.respaldo_s3 import AlmacenRespaldosS3, RespaldoNoConfigurado
from config.settings import Settings
from core.ports.almacen_respaldos import AlmacenRespaldoError
from core.services.respaldo_service import clave_respaldo, ejecutar_respaldo
from scripts.respaldar_base import comando_pg_dump

AHORA = datetime(2026, 11, 13, 8, 0, tzinfo=UTC)


class _Almacen:
    """In-memory store; `corromper` makes it report a wrong size."""

    def __init__(self, claves: list[str] | None = None, corromper: bool = False) -> None:
        self.claves = list(claves or [])
        self.corromper = corromper
        self.borradas: list[str] = []

    def subir(self, archivo: Path, clave: str) -> int:
        self.claves.append(clave)
        tam = archivo.stat().st_size
        return tam - 1 if self.corromper else tam

    def listar(self, prefijo: str) -> list[str]:
        return sorted(c for c in self.claves if c.startswith(prefijo))

    def borrar(self, clave: str) -> None:
        self.claves.remove(clave)
        self.borradas.append(clave)


def _volcar(contenido: bytes = b"PGDMP-datos") -> object:
    def volcar(destino: Path) -> None:
        destino.write_bytes(contenido)

    return volcar


def test_key_sorts_chronologically_and_is_in_utc() -> None:
    assert clave_respaldo("newsroom", AHORA) == "newsroom/2026/newsroom-2026-11-13T0800Z.dump"
    assert clave_respaldo("n", datetime(2026, 11, 13, 3, 0, tzinfo=UTC)) < clave_respaldo(
        "n", AHORA
    )


def test_backup_uploads_verifies_and_reports() -> None:
    almacen = _Almacen()

    res = ejecutar_respaldo(_volcar(), almacen, prefijo="newsroom", conservar=30, ahora=AHORA)  # type: ignore[arg-type]

    assert res.clave in almacen.claves and res.bytes == len(b"PGDMP-datos") and res.borrados == []


def test_old_backups_beyond_the_limit_are_pruned_oldest_first() -> None:
    viejas = [f"newsroom/2026/newsroom-2026-11-0{d}T0800Z.dump" for d in range(1, 6)]
    almacen = _Almacen(viejas)

    res = ejecutar_respaldo(_volcar(), almacen, prefijo="newsroom", conservar=3, ahora=AHORA)  # type: ignore[arg-type]

    assert res.borrados == viejas[:3]
    assert len(almacen.claves) == 3 and res.clave in almacen.claves


def test_an_empty_dump_is_an_error_and_nothing_is_uploaded_or_pruned() -> None:
    almacen = _Almacen(["newsroom/2026/newsroom-2026-11-01T0800Z.dump"])

    with pytest.raises(AlmacenRespaldoError):
        ejecutar_respaldo(_volcar(b""), almacen, prefijo="newsroom", conservar=1, ahora=AHORA)  # type: ignore[arg-type]

    assert almacen.borradas == [] and len(almacen.claves) == 1


def test_a_size_mismatch_fails_without_deleting_the_last_good_copy() -> None:
    buena = "newsroom/2026/newsroom-2026-11-12T0800Z.dump"
    almacen = _Almacen([buena], corromper=True)

    with pytest.raises(AlmacenRespaldoError, match="descarta"):
        ejecutar_respaldo(_volcar(), almacen, prefijo="newsroom", conservar=1, ahora=AHORA)  # type: ignore[arg-type]

    assert buena in almacen.claves and almacen.borradas == []


def test_a_failing_dump_propagates() -> None:
    def roto(destino: Path) -> None:
        raise AlmacenRespaldoError("pg_dump falló")

    with pytest.raises(AlmacenRespaldoError):
        ejecutar_respaldo(roto, _Almacen(), prefijo="n", conservar=1, ahora=AHORA)


def _settings(**kw: object) -> Settings:
    base: dict[str, object] = {
        "respaldo_s3_endpoint": "https://x.r2.cloudflarestorage.com",
        "respaldo_s3_bucket": "respaldos",
        "respaldo_s3_access_key_id": "ID-SECRETO",
        "respaldo_s3_secret_access_key": "CLAVE-SECRETA",
    }
    base.update(kw)
    return Settings(_env_file=None, **base)  # type: ignore[call-arg, arg-type]


def test_the_s3_store_needs_all_four_settings() -> None:
    with pytest.raises(RespaldoNoConfigurado):
        AlmacenRespaldosS3(_settings(respaldo_s3_bucket=None))


def test_the_s3_store_uploads_and_returns_the_stored_size(tmp_path: Path) -> None:
    archivo = tmp_path / "a.dump"
    archivo.write_bytes(b"12345")
    s3 = MagicMock()
    s3.head_object.return_value = {"ContentLength": 5}

    tam = AlmacenRespaldosS3(_settings(), cliente=s3).subir(archivo, "n/a.dump")

    assert tam == 5
    s3.upload_file.assert_called_once_with(str(archivo), "respaldos", "n/a.dump")


def test_the_s3_store_lists_across_pages_sorted() -> None:
    s3 = MagicMock()
    s3.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": "n/b"}, {"Key": "n/a"}]},
        {"Contents": [{"Key": "n/c"}]},
        {},
    ]

    assert AlmacenRespaldosS3(_settings(), cliente=s3).listar("n/") == ["n/a", "n/b", "n/c"]


def test_s3_errors_never_leak_the_keys(tmp_path: Path) -> None:
    archivo = tmp_path / "a.dump"
    archivo.write_bytes(b"1")
    s3 = MagicMock()
    s3.upload_file.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "CLAVE-SECRETA ID-SECRETO"}}, "PutObject"
    )

    with pytest.raises(AlmacenRespaldoError) as err:
        AlmacenRespaldosS3(_settings(), cliente=s3).subir(archivo, "n/a.dump")

    assert "CLAVE-SECRETA" not in str(err.value) and "ID-SECRETO" not in str(err.value)


def test_pg_dump_command_keeps_the_password_out_of_the_command_line(tmp_path: Path) -> None:
    comando, entorno = comando_pg_dump(
        "postgresql+psycopg://usuario:Contr4seña@db.railway.internal:5432/railway",
        tmp_path / "x.dump",
    )

    assert comando[0] == "pg_dump" and "--format=custom" in comando
    assert "--host=db.railway.internal" in comando and "--dbname=railway" in comando
    assert all("Contr4seña" not in parte for parte in comando)
    assert entorno["PGPASSWORD"] == "Contr4seña"


def test_only_postgres_is_supported(tmp_path: Path) -> None:
    with pytest.raises(AlmacenRespaldoError):
        comando_pg_dump("sqlite:///x.db", tmp_path / "x.dump")


def test_a_failed_upload_wrapper_from_boto3_is_also_a_clean_error(tmp_path: Path) -> None:
    archivo = tmp_path / "a.dump"
    archivo.write_bytes(b"1")
    s3 = MagicMock()
    s3.upload_file.side_effect = S3UploadFailedError("Failed to upload: SignatureDoesNotMatch")

    with pytest.raises(AlmacenRespaldoError, match="S3UploadFailedError"):
        AlmacenRespaldosS3(_settings(), cliente=s3).subir(archivo, "n/a.dump")
