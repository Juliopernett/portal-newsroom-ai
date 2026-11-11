"""chart: cortes semanales y ediciones

Revision ID: a5c8e1d7b9f2
Revises: e4a7c9b1d3f5
Create Date: 2026-11-11 20:00:00.000000

El chart pasa a ediciones semanales cerradas el viernes a medianoche (hora de
Colombia). `chart_cortes` guarda las vistas totales de todo el catalogo en cada
cierre; `chart_ediciones` + `chart_edicion_filas` guardan cada edicion
(borrador hasta que el editor la publica) con sus filas congeladas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a5c8e1d7b9f2"
down_revision: str | Sequence[str] | None = "e4a7c9b1d3f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chart_cortes",
        sa.Column("video_id", sa.String(32), nullable=False),
        sa.Column("semana_fin", sa.Date(), nullable=False),
        sa.Column("vistas", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["chart_videos.video_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("video_id", "semana_fin"),
    )
    op.create_index("ix_chart_cortes_semana_fin", "chart_cortes", ["semana_fin"])
    op.create_table(
        "chart_ediciones",
        sa.Column("semana_fin", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(16), nullable=False, server_default="borrador"),
        sa.Column("sin_base", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publicada_en", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("semana_fin"),
    )
    op.create_table(
        "chart_edicion_filas",
        sa.Column("semana_fin", sa.Date(), nullable=False),
        sa.Column("posicion", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.String(32), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("artista", sa.String(200), nullable=True),
        sa.Column("miniatura_url", sa.String(500), nullable=True),
        sa.Column("url", sa.String(200), nullable=False),
        sa.Column("vistas_semana", sa.BigInteger(), nullable=False),
        sa.Column("vistas_totales", sa.BigInteger(), nullable=False),
        sa.Column("tendencia", sa.String(16), nullable=True),
        sa.Column("posicion_anterior", sa.Integer(), nullable=True),
        sa.Column("fijado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["semana_fin"], ["chart_ediciones.semana_fin"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("semana_fin", "posicion"),
    )


def downgrade() -> None:
    op.drop_table("chart_edicion_filas")
    op.drop_table("chart_ediciones")
    op.drop_index("ix_chart_cortes_semana_fin", table_name="chart_cortes")
    op.drop_table("chart_cortes")
