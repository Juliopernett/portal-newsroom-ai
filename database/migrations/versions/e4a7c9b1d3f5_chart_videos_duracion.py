"""chart_videos.duracion_segundos

Revision ID: e4a7c9b1d3f5
Revises: d3f6b8a0c2e4
Create Date: 2026-11-10 22:00:00.000000

Duración de cada video, para dejar los Shorts (60 s o menos) fuera del
chart. YouTube no los marca en su API; la duración sale de la misma consulta
que trae las vistas. Nula hasta la siguiente medición.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4a7c9b1d3f5"
down_revision: str | Sequence[str] | None = "d3f6b8a0c2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("chart_videos") as batch:
        batch.add_column(sa.Column("duracion_segundos", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chart_videos") as batch:
        batch.drop_column("duracion_segundos")
