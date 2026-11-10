"""chart vallenato: canales, videos y snapshots de vistas

Revision ID: d3f6b8a0c2e4
Revises: c2e5a7b9d1f3
Create Date: 2026-11-10 20:00:00.000000

Chart Vallenato automático desde YouTube: los canales que se siguen, los
videos descubiertos (con las decisiones del editor: excluir / fijar) y una
foto diaria del total de vistas de cada video. Las vistas de la semana se
calculan restando fotos; YouTube no entrega "vistas por semana".
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3f6b8a0c2e4"
down_revision: str | Sequence[str] | None = "c2e5a7b9d1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chart_canales",
        sa.Column("canal_id", sa.String(length=64), primary_key=True),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("artista", sa.String(length=200), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "chart_videos",
        sa.Column("video_id", sa.String(length=32), primary_key=True),
        sa.Column("canal_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("artista", sa.String(length=200), nullable=True),
        sa.Column("publicado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("miniatura_url", sa.String(length=500), nullable=True),
        sa.Column("excluido", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fijado_posicion", sa.Integer(), nullable=True),
        sa.Column("manual", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "chart_snapshots",
        sa.Column(
            "video_id",
            sa.String(length=32),
            sa.ForeignKey("chart_videos.video_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("fecha", sa.Date(), primary_key=True),
        sa.Column("vistas", sa.BigInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("chart_snapshots")
    op.drop_table("chart_videos")
    op.drop_table("chart_canales")
