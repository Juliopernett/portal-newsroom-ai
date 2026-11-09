"""destinos_publicacion.texto_ia

Revision ID: c2e5a7b9d1f3
Revises: b1d4f6a8c2e0
Create Date: 2026-11-06 10:00:00.000000

Texto por red (Facebook/Instagram) preparado con IA a pedido del operador.
Opcional: nulo cuando el cliente ya trae su texto definitivo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2e5a7b9d1f3"
down_revision: str | Sequence[str] | None = "b1d4f6a8c2e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("destinos_publicacion") as batch:
        batch.add_column(sa.Column("texto_ia", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("destinos_publicacion") as batch:
        batch.drop_column("texto_ia")
