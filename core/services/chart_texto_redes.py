"""Caption for social media that goes with the weekly Radar Vallenato cards.

Built from the edition's rows alone (no AI, no network), so the editor gets the
same text every time and can tweak it before posting.
"""

from __future__ import annotations

from datetime import date, timedelta

from core.entities.chart import FilaEdicion

URL_RADAR = "https://portalvallenato.com/chart-vallenato/"
_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_FLECHA = {"sube": "🔼", "baja": "🔽", "igual": "▪️", "nuevo": "🆕"}
_NUMEROS = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")


def _rango(semana_fin: date) -> str:
    inicio = semana_fin - timedelta(days=6)
    if inicio.month == semana_fin.month:
        return f"del {inicio.day} al {semana_fin.day} de {_MESES[semana_fin.month - 1]}"
    return (
        f"del {inicio.day} de {_MESES[inicio.month - 1]} "
        f"al {semana_fin.day} de {_MESES[semana_fin.month - 1]}"
    )


def _linea(f: FilaEdicion) -> str:
    quien = f" — {f.artista}" if f.artista else ""
    flecha = _FLECHA.get(f.tendencia or "", "")
    return f"{_NUMEROS[f.posicion - 1]} {f.titulo}{quien} {flecha}".rstrip()


def _etiqueta(artista: str) -> str:
    solo = "".join(c for c in artista.title() if c.isalnum())
    return f"#{solo}" if solo else ""


def texto_redes(filas: list[FilaEdicion], semana_fin: date) -> str:
    """Caption: headline with the #1, the Top 10, a note on movers, link and hashtags."""
    top = sorted(filas, key=lambda f: f.posicion)[:10]
    if not top:
        return ""
    primero = top[0]
    quien = f" de {primero.artista}" if primero.artista else ""
    partes = [
        f"🎶 RADAR VALLENATO · {_rango(semana_fin)}",
        "",
        f"👑 «{primero.titulo}»{quien} manda esta semana en YouTube.",
        "",
        "El Top 10 de las canciones vallenatas más escuchadas:",
        "",
        *[_linea(f) for f in top],
    ]

    notas: list[str] = []
    nuevos = [f for f in top if f.tendencia == "nuevo"]
    if nuevos:
        nombres = ", ".join(f"«{f.titulo}»" for f in nuevos[:3])
        notas.append(f"🆕 Entran al Radar: {nombres}.")
    suben = [
        f
        for f in top
        if f.tendencia == "sube" and f.posicion_anterior and f.posicion_anterior > f.posicion
    ]
    if suben:
        s = max(suben, key=lambda f: f.posicion_anterior - f.posicion)  # type: ignore[operator]
        notas.append(
            f"🚀 Mayor salto: «{s.titulo}», del puesto {s.posicion_anterior} al {s.posicion}."
        )
    if notas:
        partes += ["", *notas]

    partes += [
        "",
        f"📊 Ranking completo y todas las noticias del vallenato: {URL_RADAR}",
        "",
        "¿Cuál es tu favorita de la semana? 👇",
    ]

    etiquetas = ["#RadarVallenato", "#Vallenato", "#PortalVallenato"]
    for f in top[:3]:
        if f.artista and (e := _etiqueta(f.artista)) and e not in etiquetas:
            etiquetas.append(e)
    partes += ["", " ".join(etiquetas)]
    return "\n".join(partes)
