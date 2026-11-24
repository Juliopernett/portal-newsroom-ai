"""chart_snapshots: me gusta y comentarios

Revision ID: f6b8d0a2c4e7
Revises: b7d2f4a6c8e1
Create Date: 2026-11-24 12:00:00.000000

Me gusta y comentarios de cada video el día de la medición, para avisar al
editor cuando las reacciones no guardan proporción con las vistas. Nulos en
las mediciones anteriores y cuando el canal oculta las cifras.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6b8d0a2c4e7"
down_revision: str | Sequence[str] | None = "b7d2f4a6c8e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("chart_snapshots") as batch:
        batch.add_column(sa.Column("me_gusta", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("comentarios", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chart_snapshots") as batch:
        batch.drop_column("comentarios")
        batch.drop_column("me_gusta")
