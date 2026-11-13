"""S3-compatible store (Cloudflare R2) for the database backups."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3
from boto3.exceptions import Boto3Error
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from config.settings import Settings
from core.ports.almacen_respaldos import AlmacenRespaldoError


class RespaldoNoConfigurado(RuntimeError):
    """The RESPALDO_S3_* variables are not all set."""


class AlmacenRespaldosS3:
    """`AlmacenRespaldos` on any S3-compatible bucket. Errors never echo the keys."""

    def __init__(self, settings: Settings, cliente: Any | None = None) -> None:
        if not (
            settings.respaldo_s3_endpoint
            and settings.respaldo_s3_bucket
            and settings.respaldo_s3_access_key_id
            and settings.respaldo_s3_secret_access_key
        ):
            raise RespaldoNoConfigurado(
                "Faltan RESPALDO_S3_ENDPOINT, RESPALDO_S3_BUCKET, RESPALDO_S3_ACCESS_KEY_ID "
                "o RESPALDO_S3_SECRET_ACCESS_KEY en Railway."
            )
        self._bucket = settings.respaldo_s3_bucket
        self._s3 = cliente or boto3.client(
            "s3",
            endpoint_url=settings.respaldo_s3_endpoint,
            aws_access_key_id=settings.respaldo_s3_access_key_id,
            aws_secret_access_key=settings.respaldo_s3_secret_access_key,
            region_name="auto",
            config=Config(retries={"max_attempts": 3, "mode": "standard"}, connect_timeout=15),
        )

    def subir(self, archivo: Path, clave: str) -> int:
        try:
            self._s3.upload_file(str(archivo), self._bucket, clave)
            cabecera = self._s3.head_object(Bucket=self._bucket, Key=clave)
        except (BotoCoreError, ClientError, Boto3Error) as exc:
            raise AlmacenRespaldoError(
                f"No se pudo subir el respaldo: {type(exc).__name__}"
            ) from None
        return int(cabecera["ContentLength"])

    def listar(self, prefijo: str) -> list[str]:
        claves: list[str] = []
        try:
            paginas = self._s3.get_paginator("list_objects_v2").paginate(
                Bucket=self._bucket, Prefix=prefijo
            )
            for pagina in paginas:
                claves.extend(o["Key"] for o in pagina.get("Contents", []))
        except (BotoCoreError, ClientError, Boto3Error) as exc:
            raise AlmacenRespaldoError(
                f"No se pudo listar los respaldos: {type(exc).__name__}"
            ) from None
        return sorted(claves)

    def borrar(self, clave: str) -> None:
        try:
            self._s3.delete_object(Bucket=self._bucket, Key=clave)
        except (BotoCoreError, ClientError, Boto3Error) as exc:
            raise AlmacenRespaldoError(f"No se pudo borrar {clave}: {type(exc).__name__}") from None
