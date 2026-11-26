"""Sample pieces to preview a colour change before saving it (made-up content)."""

from __future__ import annotations

import io
from datetime import date

from PIL import Image

from agents.images.pillow_chart_renderer import FilaImagen, PillowChartRenderer
from agents.images.pillow_portada_renderer import PillowPortadaRenderer
from core.entities.colores_marca import ColoresMarca
from core.ports.portada_renderer import SolicitudPortada


def _foto_de_muestra() -> bytes:
    """A neutral gradient standing in for a news photo."""
    degradado = Image.linear_gradient("L").resize((1080, 1350))
    foto = Image.composite(
        Image.new("RGB", degradado.size, (96, 74, 62)),
        Image.new("RGB", degradado.size, (214, 205, 196)),
        degradado,
    )
    salida = io.BytesIO()
    foto.save(salida, "JPEG", quality=90)
    return salida.getvalue()


def portada_de_muestra(colores: ColoresMarca) -> bytes:
    return PillowPortadaRenderer(colores).renderizar(
        SolicitudPortada(
            imagen_base=_foto_de_muestra(),
            antetitulo="¡Así se ve el gancho!",
            titular="Este es un titular de muestra para revisar los colores de las portadas",
        )
    )


def radar_de_muestra(colores: ColoresMarca) -> bytes:
    filas = [
        FilaImagen(
            posicion=i,
            titulo=f"Canción de muestra {i}",
            artista=f"Artista {i}",
            vistas_semana=900_000 // i,
            tendencia=("sube", "baja", "igual", "nuevo")[i % 4],
        )
        for i in range(1, 11)
    ]
    return PillowChartRenderer(colores).renderizar(date(2026, 11, 27), filas, lamina="lista")
