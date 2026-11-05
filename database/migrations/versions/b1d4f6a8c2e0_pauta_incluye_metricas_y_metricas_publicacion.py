"""pautas.incluye_metricas + metricas_publicacion table

Revision ID: b1d4f6a8c2e0
Revises: a9e1c7d3f5b6
Create Date: 2026-11-05 16:00:00.000000

Informe con métricas (opcional por contrato): `pautas.incluye_metricas`
decide si el informe del cliente muestra alcance/interacciones, y
`metricas_publicacion` guarda la última captura de Meta por destino
(Facebook/Instagram) — se guarda en vez de pedirla en vivo para no depender
de Meta cada vez que se abre o descarga un informe.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1d4f6a8c2e0"
down_revision: str | Sequence[str] | None = "a9e1c7d3f5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("pautas") as batch:
        batch.add_column(
            sa.Column("incluye_metricas", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.create_table(
        "metricas_publicacion",
        sa.Column(
            "destino_id",
            sa.String(length=36),
            sa.ForeignKey("destinos_publicacion.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("alcance", sa.Integer(), nullable=True),
        sa.Column("vistas", sa.Integer(), nullable=True),
        sa.Column("reacciones", sa.Integer(), nullable=True),
        sa.Column("comentarios", sa.Integer(), nullable=True),
        sa.Column("compartidos", sa.Integer(), nullable=True),
        sa.Column("guardados", sa.Integer(), nullable=True),
        sa.Column("capturado_en", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("metricas_publicacion")
    with op.batch_alter_table("pautas") as batch:
        batch.drop_column("incluye_metricas")
