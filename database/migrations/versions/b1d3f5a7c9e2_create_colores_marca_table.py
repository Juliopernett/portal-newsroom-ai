"""create colores_marca table

Revision ID: b1d3f5a7c9e2
Revises: f6b8d0a2c4e7
Create Date: 2026-11-26 00:00:00.000000

No seed row: while the table is empty the app uses the website's colours
(the defaults of `core.entities.colores_marca.ColoresMarca`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1d3f5a7c9e2"
down_revision: str | Sequence[str] | None = "f6b8d0a2c4e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "colores_marca",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("fondo", sa.String(length=7), nullable=False),
        sa.Column("destacado", sa.String(length=7), nullable=False),
        sa.Column("texto_destacado", sa.String(length=7), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("colores_marca")
