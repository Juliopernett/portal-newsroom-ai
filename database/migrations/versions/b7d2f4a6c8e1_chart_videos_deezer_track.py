"""chart_videos.deezer_track_id

Revision ID: b7d2f4a6c8e1
Revises: a5c8e1d7b9f2
Create Date: 2026-11-23 12:00:00.000000

Canción de Deezer elegida a mano para un video del chart (el emparejamiento
automático a veces toma otra versión, p. ej. el estudio en vez del "en vivo").
Nula = automático; "ninguna" = no mostrar la etiqueta de Deezer.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2f4a6c8e1"
down_revision: str | Sequence[str] | None = "a5c8e1d7b9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("chart_videos") as batch:
        batch.add_column(sa.Column("deezer_track_id", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chart_videos") as batch:
        batch.drop_column("deezer_track_id")
