"""Safe reading of uploaded files.

Two gaps this closes (security audit 2026-11-05): the whole upload used to
be read into memory *before* its size was checked (a 2 GB body would be
buffered first), and the client-declared `Content-Type` was trusted with
no look at the bytes.
"""

from __future__ import annotations

from fastapi import HTTPException, UploadFile

_CHUNK = 1024 * 1024

_IMAGE_SIGNATURES: tuple[tuple[str, bytes], ...] = (
    ("image/jpeg", b"\xff\xd8\xff"),
    ("image/png", b"\x89PNG\r\n\x1a\n"),
    ("image/gif", b"GIF87a"),
    ("image/gif", b"GIF89a"),
)


def _looks_like(content_type: str, head: bytes) -> bool:
    if content_type == "image/webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return any(ct == content_type and head.startswith(sig) for ct, sig in _IMAGE_SIGNATURES)


async def read_limited(archivo: UploadFile, max_bytes: int) -> bytes:
    """Read `archivo` in chunks; raise 413 as soon as it exceeds `max_bytes`."""
    partes: list[bytes] = []
    total = 0
    while chunk := await archivo.read(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413, detail=f"El archivo supera el máximo de {max_bytes} bytes"
            )
        partes.append(chunk)
    return b"".join(partes)


def ensure_image_matches_type(content_type: str, contenido: bytes) -> None:
    """422 unless the bytes really are the image type the client declared."""
    if not _looks_like(content_type, contenido[:16]):
        raise HTTPException(
            status_code=422, detail="El contenido del archivo no coincide con su tipo de imagen"
        )
