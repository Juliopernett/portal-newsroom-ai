"""Alert for songs whose reactions do not match their views (pure logic, no network).

A song that gains a million views in a week but almost no likes or comments is
what bought, looped or automated plays look like. The signal is only a hint for
the editor, who decides: paid promotion, a viral clip or a very young audience
also give few reactions. So nothing is excluded here, only flagged.

Each song is compared with the *median of the chart's own songs*: the figure that
counts is reactions per view over the last week when the history allows it
(`likes gained / views gained`), otherwise over the whole life of the video.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from core.entities.chart import SnapshotVistas

MIN_CANCIONES = 4  # fewer songs than this and a median means nothing
UMBRAL_ME_GUSTA = 0.35  # flagged below 35 % of the median likes per view
UMBRAL_COMENTARIOS = 0.20  # comments vary more between songs: a lower bar
MIN_VISTAS_SEMANA = 50_000  # below this a week's figure is too noisy: use the lifetime ratio
MIN_VISTAS_TOTALES = 20_000
DIAS_SEMANA = 7


@dataclass(frozen=True, slots=True)
class AlertaReaccion:
    motivo: str
    me_gusta_pct: float | None  # likes per 100 views (the figure used)
    comentarios_pct: float | None
    base: str  # "semana" | "total": which period the ratio covers


def _pct(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",") + " %"


def _razon(
    snaps: list[SnapshotVistas], fin: date, campo: str
) -> tuple[float, str, int, int] | None:
    """(reactions per view, "semana"|"total", views, reactions) as of `fin`, or None."""
    validos = sorted(
        (s for s in snaps if s.fecha <= fin and getattr(s, campo) is not None),
        key=lambda s: s.fecha,
    )
    if not validos:
        return None
    ultimo = validos[-1]
    if ultimo.vistas < MIN_VISTAS_TOTALES:
        return None
    base = None
    for s in validos:
        if s.fecha <= ultimo.fecha - timedelta(days=DIAS_SEMANA):
            base = s
    if base is not None:
        dv = ultimo.vistas - base.vistas
        dr = getattr(ultimo, campo) - getattr(base, campo)
        if dv >= MIN_VISTAS_SEMANA and dr >= 0:
            return dr / dv, "semana", dv, dr
    return getattr(ultimo, campo) / ultimo.vistas, "total", ultimo.vistas, getattr(ultimo, campo)


def evaluar_reacciones(
    canciones: dict[str, list[SnapshotVistas]], fin: date
) -> dict[str, AlertaReaccion]:
    """Flag the songs whose likes or comments per view fall far below the group's median.

    `canciones` maps each chart song to its snapshots. Songs with no reaction figures
    (old snapshots, hidden likes) are never flagged and do not count for the median.
    """
    me_gusta = {k: r for k, s in canciones.items() if (r := _razon(s, fin, "me_gusta"))}
    comentarios = {k: r for k, s in canciones.items() if (r := _razon(s, fin, "comentarios"))}
    med_mg = median(r[0] for r in me_gusta.values()) if len(me_gusta) >= MIN_CANCIONES else None
    med_co = (
        median(r[0] for r in comentarios.values()) if len(comentarios) >= MIN_CANCIONES else None
    )

    alertas: dict[str, AlertaReaccion] = {}
    for vid in canciones:
        motivos: list[str] = []
        mg, co = me_gusta.get(vid), comentarios.get(vid)
        if mg and med_mg and mg[0] < UMBRAL_ME_GUSTA * med_mg:
            motivos.append(
                f"{_pct(mg[0] * 100)} de las vistas dieron me gusta; en el Top lo normal es "
                f"{_pct(med_mg * 100)}"
            )
        if co and med_co and co[0] < UMBRAL_COMENTARIOS * med_co:
            motivos.append(
                f"{_pct(co[0] * 100)} de comentarios por vista; en el Top lo normal es "
                f"{_pct(med_co * 100)}"
            )
        if not motivos:
            continue
        base = (mg or co)[1]  # type: ignore[index]
        periodo = "esta semana" if base == "semana" else "en toda su vida"
        alertas[vid] = AlertaReaccion(
            motivo=f"Pocas reacciones para tantas vistas ({periodo}): " + "; ".join(motivos) + ".",
            me_gusta_pct=round(mg[0] * 100, 3) if mg else None,
            comentarios_pct=round(co[0] * 100, 3) if co else None,
            base=base,
        )
    return alertas
